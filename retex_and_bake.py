import bpy
import os
import itertools
from mathutils import Euler, Vector
import math
import numpy as np
from PIL import Image
from utils import import_glb_merge_vertices
from pathlib import Path

DENOISE = True  # Set to True if you want to use denoising

class Material():
    # Each argument should contain a filepath to the image
    def __init__(self, name, diffuse, roughness=None, metallic=None, normal=None, ao=None, orm=None, scale=1.0):
        self.name = name
        self.diffuse = diffuse
        self.roughness = roughness
        self.metallic = metallic
        self.normal = normal
        self.ao = ao
        self.orm = orm    # new attribute for Occlusion/Roughness/Metallic texture
        self.scale = scale


    # helper to create a blender material with nodes
    @staticmethod
    def make_blender_material(name):
        mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()
        out = nodes.new('ShaderNodeOutputMaterial')
        out.location = (300, 0)
        bsdf = nodes.new('ShaderNodeBsdfPrincipled')
        bsdf.location = (0, 0)
        links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
        return mat, nodes, links, bsdf
    

    # helper to set up UV→Mapping once per material
    def add_uv_mapping(self, nodes, links):
        coord = nodes.new('ShaderNodeTexCoord')
        coord.location = (-900, 200)
        mapping = nodes.new('ShaderNodeMapping')
        mapping.location = (-600, 200)
        mapping.inputs['Scale'].default_value = (self.scale, self.scale, self.scale)
        links.new(coord.outputs['UV'], mapping.inputs['Vector'])
        return mapping
    

def bake_texture(mesh, img_name, image_size, denoise, bake_dir=None):
    #Create blank image
    img = bpy.data.images.new(img_name, width=image_size, height=image_size)

    # 3) In each material’s node tree, add an Image Texture node pointing to our image,
    #    and make it the active bake target
    for slot in mesh.material_slots:

        nodes = slot.material.node_tree.nodes
        # un‑select everything
        for n in nodes:
            n.select = False
        bake_node = nodes.new('ShaderNodeTexImage')
        bake_node.image = img
        bake_node.select = True
        nodes.active = bake_node

        # 4) Bake!
    if mesh:
        for poly in mesh.data.polygons:
            poly.use_smooth = True

    mesh.data.use_auto_smooth = True
    mesh.data.auto_smooth_angle = math.radians(30)  # adjust as needed
    mesh.data.update()  # refresh the data

    print("Baking texture:", img_name)
    bpy.context.scene.cycles.device = "GPU"  # use GPU if available
    bpy.context.scene.cycles.use_denoising = denoise  # disable denoising to fix seam issues
    bpy.ops.object.bake(type='COMBINED', use_clear=True)
    print("Bake complete")

    if bake_dir:
        # # 5) Save out the result
        # img.filepath_raw = os.path.join(bake_dir, img_name + ".png")
        # img.file_format = 'PNG'
        # img.save()

        # 5) Save out the result as JPEG at 95% quality
        jpg_filepath = os.path.join(bake_dir, img_name + ".jpg")
        img.filepath_raw = jpg_filepath
        img.file_format = 'JPEG'
        img.save(quality=95)

    else:
        # Retrieve pixel data from the baked image
        # Blender stores pixels as a flat array (R, G, B, A, R, G, B, A, ...)
        pixel_data = np.array(img.pixels[:])
        # Convert values to 0-255 and cast to uint8
        pixel_data = (pixel_data * 255).astype(np.uint8)
        # Reshape to (height, width, 4)
        pixel_data = pixel_data.reshape((image_size, image_size, 4))
        pil_img = Image.fromarray(pixel_data, mode="RGBA")

    # 6) Cleanup: remove the bake‐target nodes and image
    for slot in mesh.material_slots:
        nodes = slot.material.node_tree.nodes
        for n in [n for n in nodes if isinstance(n, bpy.types.ShaderNodeTexImage) and n.image == img]:
            nodes.remove(n)
    bpy.data.images.remove(img)

    if not bake_dir:
        # Return the PIL image for further processing or saving
        return pil_img
  
    

def apply_material(mesh, material, slot):
    # helper to add an Image Texture node and link its vector
    def add_image(nodes, links, mapping, path, loc):
        if not path or not os.path.isfile(path):
            print(f"Warning: missing texture: {path}")
            return None
        
        # change to absolute path for blender
        path = str(Path(path).resolve())
        img = bpy.data.images.load(path)
        img_node = nodes.new('ShaderNodeTexImage')
        img_node.image = img
        img_node.location = loc
        links.new(mapping.outputs['Vector'], img_node.inputs['Vector'])
        return img_node


    name = material.name
    print("Applying material name:", name)

    mat, nodes, links, bsdf = material.make_blender_material(name)
    mapping = material.add_uv_mapping(nodes, links)

    # Diffuse → Base Color
    d = add_image(nodes, links, mapping, material.diffuse,   loc=(-300, 300))
    if d:
        links.new(d.outputs['Color'], bsdf.inputs['Base Color'])

    # Roughness → Roughness
    r = add_image(nodes, links, mapping, material.roughness, loc=(-300, 150))
    if r:
        links.new(r.outputs['Color'], bsdf.inputs['Roughness'])

    # Metallic → Metallic
    m = add_image(nodes, links, mapping, material.metallic,  loc=(-300, 0))
    if m:
        links.new(m.outputs['Color'], bsdf.inputs['Metallic'])

    # Normal → NormalMap → Normal
    n = add_image(nodes, links, mapping, material.normal,    loc=(-300, -150))
    if n:
        norm_map = nodes.new('ShaderNodeNormalMap')
        norm_map.location = (0, -150)
        links.new(n.outputs['Color'], norm_map.inputs['Color'])
        links.new(norm_map.outputs['Normal'], bsdf.inputs['Normal'])

    ao = add_image(nodes, links, mapping, material.ao, loc=(-300, -300))
    if ao:
        if d:
            mix_occlusion = nodes.new('ShaderNodeMixRGB')
            mix_occlusion.blend_type = 'MULTIPLY'
            mix_occlusion.location = (-100, 300)
            mix_occlusion.inputs['Fac'].default_value = 1.0
            # Disconnect the original diffuse connection from Base Color if needed.
            # Here we assume that connecting the mix node later will override it.
            links.new(d.outputs['Color'], mix_occlusion.inputs[1])
            links.new(ao.outputs['Color'], mix_occlusion.inputs[2])
            links.new(mix_occlusion.outputs['Color'], bsdf.inputs['Base Color'])


    # ORM: Occlusion/Roughness/Metallic combined texture
    if material.orm:
        orm_node = add_image(nodes, links, mapping, material.orm, loc=(-300, -300))
        if orm_node:
            sep_rgb = nodes.new('ShaderNodeSeparateRGB')
            sep_rgb.location = (-100, -300)
            links.new(orm_node.outputs['Color'], sep_rgb.inputs[0])
            # Use G for Roughness and B for Metallic, overriding previous ones if desired
            links.new(sep_rgb.outputs['G'], bsdf.inputs['Roughness'])
            links.new(sep_rgb.outputs['B'], bsdf.inputs['Metallic'])
            # For Occlusion: multiply the diffuse color with R. Create a MixRGB node.
            if d:
                mix_occlusion = nodes.new('ShaderNodeMixRGB')
                mix_occlusion.blend_type = 'MULTIPLY'
                mix_occlusion.location = (-100, 300)
                mix_occlusion.inputs['Fac'].default_value = 1.0
                # Disconnect the original diffuse connection from Base Color if needed.
                # Here we assume that connecting the mix node later will override it.
                links.new(d.outputs['Color'], mix_occlusion.inputs[1])
                links.new(sep_rgb.outputs['R'], mix_occlusion.inputs[2])
                links.new(mix_occlusion.outputs['Color'], bsdf.inputs['Base Color'])


    # assign the material to the desired slot only if that slot exists and is not empty
    if slot < len(mesh.material_slots):
        if mesh.material_slots[slot].material:
            mesh.material_slots[slot].material = mat
            print(f"Material '{name}' assigned to slot {slot}.")
        else:
            print(f"Slot {slot} is empty; not assigning material.")
    else:
        print(f"Slot {slot} does not exist on the object; no material assigned.")


def bake_materials_seperately(materials, mesh, resolution, denoise, samples, bake_dir=None):
    if not bake_dir:
        img_list = []
    else:
        # ensure output folder exists
        os.makedirs(bake_dir, exist_ok=True)

    if mesh is None:
        raise RuntimeError("No mesh object found. Please check the model path.")

    # force Cycles
    bpy.context.scene.render.engine = "CYCLES"
    # Set the device_type
    bpy.context.preferences.addons[
        "cycles"
    ].preferences.compute_device_type = "CUDA"

    bpy.context.scene.cycles.device = "GPU"  # use GPU if available

    # get_devices() to let Blender detects GPU device
    bpy.context.preferences.addons["cycles"].preferences.get_devices()
    print(bpy.context.preferences.addons["cycles"].preferences.compute_device_type)
    for d in bpy.context.preferences.addons["cycles"].preferences.devices:
        d["use"] = 1 # Using all devices, include GPU and CPU
        print(d["name"], d["use"])

    bpy.context.scene.cycles.bake_type = 'COMBINED'
    bpy.context.scene.cycles.samples = samples  # adjust as needed

    # ensure our object is active/selected
    # bpy.ops.object.select_all(action='DESELECT')
    mesh.select_set(True)
    bpy.context.view_layer.objects.active = mesh

    # make sure there's at least one UV map
    if not mesh.data.uv_layers:
        mesh.data.uv_layers.new(name="UVMap")

    if len(mesh.material_slots) == 0:
         bpy.data.materials.new("Material")

    for i in range(len(materials)):
        group_bake_dir = os.path.join(bake_dir, f"material_group_{i}")
        os.makedirs(group_bake_dir, exist_ok=True)
        group = materials[i]
        if i > len(mesh.material_slots):
            print(f"Warning: Not enough material slots for group {i}.")
            break
        for mat in group:
            apply_material(mesh, mat, i)

            name = mat.name
            if bake_dir:
                bake_texture(mesh, name, bake_dir=group_bake_dir, image_size=resolution, denoise=denoise)
            else:
                img_list.append(bake_texture(mesh, name, image_size=resolution, denoise=denoise))
    

    if not bake_dir:
        # Return the list of PIL images for further processing or saving
        return img_list


def setup_hdri_environment(model_path: str, hdri_path: str, strength: float = 1.0):
    """
    Sets up the World environment to use an HDRI texture (.exr) for lighting,
    and sets the background strength.
    
    Parameters:
        hdri_path (str): Full file path to the HDRI .exr image.
        strength (float): Strength of the HDRI lighting. Default is 1.0.
    """
    # Select and delete all objects in the scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # Import the GLB
    # bpy.ops.wm.obj_import(filepath=str(model_path))
    mesh_obj = import_glb_merge_vertices(model_path)

    if mesh_obj is None:
        raise RuntimeError(f"No mesh object found in {model_path}. Check the file format/path.")

    # Get the current world or create one if missing.
    if not bpy.context.scene.world:
        bpy.context.scene.world = bpy.data.worlds.new("World")
    world = bpy.context.scene.world
    world.use_nodes = True
    node_tree = world.node_tree
    nodes = node_tree.nodes
    links = node_tree.links

    # Clear all existing nodes
    for node in nodes:
        nodes.remove(node)

    # Create nodes: Environment Texture, Background, and World Output.
    env_tex = nodes.new(type="ShaderNodeTexEnvironment")
    env_tex.location = (-300, 300)
    try:
        env_tex.image = bpy.data.images.load(hdri_path)
    except Exception as e:
        print(f"Failed to load HDRI image from {hdri_path}: {e}")
        return

    bg_node = nodes.new(type="ShaderNodeBackground")
    bg_node.location = (0, 300)
    bg_node.inputs['Strength'].default_value = strength

    output_node = nodes.new(type="ShaderNodeOutputWorld")
    output_node.location = (200, 300)

    # Link Environment Texture -> Background -> World Output
    links.new(env_tex.outputs['Color'], bg_node.inputs['Color'])
    links.new(bg_node.outputs['Background'], output_node.inputs['Surface'])

    return mesh_obj


def read_json_materials(json_path):
    """
    Reads a JSON file containing material information and returns a dictionary of materials.
    
    Parameters:
        json_path (str): Path to the JSON file.
        
    Returns:
        dict: Dictionary containing material names as keys and Material objects as values.
    """
    import json
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    material_list = []

    for group in data:
        group_materials = []
        for material in group:
            # Creates Material objects for each material in the JSON file
            # Values without a default are set to None if not found
            group_materials.append(
                Material(
                    name=material.get("name"),
                    diffuse=material.get("diffuse"),
                    roughness=material.get("roughness"),
                    metallic=material.get("metallic"),
                    normal=material.get("normal"),
                    ao=material.get("ambient_occlusion"),
                    orm=material.get("orm"),
                    scale=material.get("scale", 1.0)
                )
            )
        material_list.append(group_materials)
    
    return material_list


# Function that applies the baked texture maps, exports the model as GLB, and removes the PNG files
def apply_and_export_glb(model_path, bake_dir):

    mesh = import_glb_merge_vertices(model_path)

    # remove all materials from the object
    for material in bpy.data.materials:
        material.user_clear()
        bpy.data.materials.remove(material)

    # Iterate through all PNG texture files in bake_dir
    png_files = [f for f in os.listdir(bake_dir) if f.lower().endswith(".png")]
    if not png_files:
        print("No PNG textures found in bake_dir.")
        return

    for png_filename in png_files:
        png_path = os.path.join(bake_dir, png_filename)
        
        # Create an emissive material using the PNG texture
        material_name = f"emissive_{os.path.splitext(png_filename)[0]}"
        mat = bpy.data.materials.new(name=material_name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # Clear all default nodes
        for node in nodes:
            nodes.remove(node)
            
        # Create necessary nodes
        tex_node = nodes.new(type="ShaderNodeTexImage")
        tex_node.location = (0, 0)

        tex_node.image = bpy.data.images.load(png_path)

        emission_node = nodes.new(type="ShaderNodeEmission")
        emission_node.location = (200, 0)
        # Optionally adjust the emissive strength
        emission_node.inputs['Strength'].default_value = 1.0

        output_node = nodes.new(type="ShaderNodeOutputMaterial")
        output_node.location = (400, 0)

        # Connect image texture to emission then to material output
        links.new(tex_node.outputs['Color'], emission_node.inputs['Color'])
        links.new(emission_node.outputs['Emission'], output_node.inputs['Surface'])

        # Assign the new emissive material to the mesh, replacing existing materials
        mesh.data.materials.clear()
        mesh.data.materials.append(mat)

        # Export the scene/model as a GLB using a unique file name
        export_filename = f"{os.path.splitext(png_filename)[0]}.glb"
        export_path = os.path.join(bake_dir, export_filename)
        bpy.ops.export_scene.gltf(filepath=export_path, export_format='GLB')


        os.remove(png_path)


import click

@click.command()
@click.option('--material_json', type=str, help='Path to the json file that specifies the materials, look at material-example.json for reference.')
@click.option('--model_path', type=str, help='Path to the .glb file you exported in step 2.')
@click.option('--hdri_path', type=str, default="hdris/studio_small_09_1k.exr", help='Path to the HDRI image (.exr).')
@click.option('--hdri_strength', type=float, default=1.0, help='Strength of the HDRI lighting. Default is 1.0.')
@click.option('--texture_size', type=int, default=4096, help='Size of the texture to bake. Default is 4096.')
@click.option('--denoise', type=bool, default=False, help='Whether to use denoising. Default is False. (Seams will appear if set to True)')
@click.option('--samples', type=int, default=40, help='Number of samples for baking. Default is 40.')
# @click.option('--export_glb', type=bool, default=False, help='Whether to export a baked GLB model instead of a texture map. Default is False.')


def retex_and_bake(model_path, material_json, hdri_path, hdri_strength, texture_size, denoise, samples, export_glb):
    """
    Main function to retouch and bake materials based on a JSON file.
    
    Parameters:
        material_json (str): Path to the JSON file containing material information.
    """
    model_path = str(Path(model_path).resolve())
    material_json = str(Path(material_json).resolve())
    hdri_path = str(Path(hdri_path).resolve())
    

    materials = read_json_materials(material_json)

    # Set up the scene with the model and HDRI environment
    mesh = setup_hdri_environment(
        model_path,
        hdri_path,
        hdri_strength
    )

    # Permutate and bake materials
    bake_materials_seperately(materials, mesh, bake_dir=os.path.join(os.path.dirname(model_path), "baked_textures"), denoise=denoise, resolution=texture_size, samples=samples)

    # if export_glb:
    #     # Export the model with baked textures as a GLB file
    #     apply_and_export_glb(model_path, os.path.join(os.path.dirname(model_path), "baked_textures"))


if __name__ == "__main__":
    retex_and_bake()