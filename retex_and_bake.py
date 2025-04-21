import bpy
import os
import itertools
from mathutils import Euler, Vector
import math

class Material():
    # Each argument should contain a filepath to the image
    def __init__(self, diffuse, roughness=None, metallic=None, normal=None, scale=20.0):
        self.diffuse = diffuse
        self.roughness = roughness
        self.metallic = metallic
        self.normal = normal
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
    

def bake_texture(obj, bake_dir, img_name, image_size=2048):
    #Create blank image
    img = bpy.data.images.new(img_name, width=image_size, height=image_size)

    # 3) In each material’s node tree, add an Image Texture node pointing to our image,
    #    and make it the active bake target
    for slot in obj.material_slots:
        nodes = slot.material.node_tree.nodes
        # un‑select everything
        for n in nodes:
            n.select = False
        bake_node = nodes.new('ShaderNodeTexImage')
        bake_node.image = img
        bake_node.select = True
        slot.material.node_tree.nodes.active = bake_node

    # 4) Bake!
    if obj:
        for poly in obj.data.polygons:
            poly.use_smooth = True

    obj.data.use_auto_smooth = True
    obj.data.auto_smooth_angle = math.radians(30)  # adjust as needed
    obj.data.update()  # refresh the data

    print("Baking texture:", img_name)
    bpy.context.scene.cycles.device = "GPU"  # use GPU if available
    bpy.ops.object.bake(type='COMBINED', use_clear=True)
    print("Bake complete")

    # 5) Save out the result
    filepath = os.path.join(bake_dir, img_name + ".png")
    img.filepath_raw = filepath
    img.file_format = 'PNG'
    img.save()

    # 6) Cleanup: remove the bake‐target nodes and image
    for slot in obj.material_slots:
        nodes = slot.material.node_tree.nodes
        for n in [n for n in nodes if isinstance(n, bpy.types.ShaderNodeTexImage) and n.image == img]:
            nodes.remove(n)
    bpy.data.images.remove(img)


def apply_materials(obj, primary, secondary, tertiary):
    """
    obj:        A mesh object.
    primary:    Material() instance with .diffuse, .roughness, .metallic, .normal
    secondary:  Material() instance
    tertiary:   Material() instance

    Builds/updates materials named "primary", "secondary", "tertiary",
    scales all their textures by 20× UV, and hooks up diffuse, roughness,
    metallic, and normal channels.
    """

    # helper to add an Image Texture node and link its vector
    def add_image(nodes, links, mapping, path, loc):
        if not path or not os.path.isfile(path):
            print(f"Warning: missing texture: {path}")
            return None
        img = bpy.data.images.load(path)
        img_node = nodes.new('ShaderNodeTexImage')
        img_node.image = img
        img_node.location = loc
        links.new(mapping.outputs['Vector'], img_node.inputs['Vector'])
        return img_node

    # package up the three slots
    slots = {
        "primary":   primary,
        "secondary": secondary,
        "tertiary":  tertiary,
    }

    for name, mat_info in slots.items():
        if not mat_info:
            continue
        print("Applying material name:", name)
        mat, nodes, links, bsdf = mat_info.make_blender_material(name)
        mapping = mat_info.add_uv_mapping(nodes, links)

        # Diffuse → Base Color
        d = add_image(nodes, links, mapping, mat_info.diffuse,   loc=(-300, 300))
        if d:
            links.new(d.outputs['Color'], bsdf.inputs['Base Color'])

        # Roughness → Roughness
        r = add_image(nodes, links, mapping, mat_info.roughness, loc=(-300, 150))
        if r:
            links.new(r.outputs['Color'], bsdf.inputs['Roughness'])

        # Metallic → Metallic
        m = add_image(nodes, links, mapping, mat_info.metallic,  loc=(-300, 0))
        if m:
            links.new(m.outputs['Color'], bsdf.inputs['Metallic'])

        # Normal → NormalMap → Normal
        n = add_image(nodes, links, mapping, mat_info.normal,    loc=(-300, -150))
        if n:
            norm_map = nodes.new('ShaderNodeNormalMap')
            norm_map.location = (0, -150)
            links.new(n.outputs['Color'], norm_map.inputs['Color'])
            links.new(norm_map.outputs['Normal'], bsdf.inputs['Normal'])

        # assign to object (replace existing or append)
        names = [s.material.name if s.material else "" for s in obj.material_slots]
        if name in names:
            idx = names.index(name)
            obj.material_slots[idx].material = mat
        else:
            obj.data.materials.append(mat)


def permutate_and_bake_materials(materials, obj, bake_dir):
    """
    materials_dict: {"primary": [M1, M2, …],
                     "secondary": […],
                     "tertiary": […]}
    obj:            Your mesh object (must be UV‑unwrapped)
    bake_dir:       Folder path where baked pngs will be saved
    image_size:     Resolution of the baked texture

    For each tuple (p, s, t) in the Cartesian product of the three lists:
      • apply_materials(obj, p, s, t)
      • create a new blank image
      • inject it into every material as the active bake target
      • bake COMBINED (diffuse+spec+norm) in Cycles
      • save to bake_dir as bake_{p.name}_{s.name}_{t.name}.png
    """
    # ensure output folder exists
    os.makedirs(bake_dir, exist_ok=True)

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
    bpy.context.scene.cycles.samples = 20  # adjust as needed

    # ensure our object is active/selected
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    # make sure there's at least one UV map
    if not obj.data.uv_layers:
        obj.data.uv_layers.new(name="UVMap")


    prim_list = materials.get('primary')   or [None]
    sec_list  = materials.get('secondary') or [None]
    ter_list  = materials.get('tertiary')  or [None]

    count = 0
    for pri, sec, ter in itertools.product(prim_list, sec_list, ter_list):

        # Report what we're baking
        print("Applying materials:",
              pri.diffuse   if pri else "—",
              sec.diffuse   if sec else "—",
              ter.diffuse   if ter else "—")

        # 1) Assign whatever is non‑None (pass None into apply_materials;
        #    your apply_materials should handle missing channels gracefully)
        apply_materials(obj, pri, sec, ter)

        print("Materials applied, baking texture")

        # 2) Bake out the texture for this combo
        bake_texture(obj, bake_dir, 'bake_' + str(count))
        count += 1


# Setups the scene with a plane and lighting, returns the mesh object
def setup_scene(model_path):
    bpy.data.objects['Cube'].select_set(True)  # delete the cube
    bpy.data.objects['Light'].select_set(True)  # Delete Light
    bpy.ops.object.delete()  # Delete selected objects

    bpy.ops.import_scene.gltf(filepath=str(model_path))
    imported_objects = list(bpy.context.selected_objects)
    mesh_obj = next((obj for obj in imported_objects if obj.type == 'MESH'), None)


    # ADD IN PLANE BELOW MESH
    # Compute world‑space bounding box corners
    wm = mesh_obj.matrix_world
    bbox_world = [wm @ Vector(corner) for corner in mesh_obj.bound_box]
    xs = [v.x for v in bbox_world]
    ys = [v.y for v in bbox_world]
    zs = [v.z for v in bbox_world]

    # center X/Y, and lowest Z
    center_x = (min(xs) + max(xs)) / 2.0
    center_y = (min(ys) + max(ys)) / 2.0
    min_z    = min(zs)

    # Add the plane
    bpy.ops.mesh.primitive_plane_add(
        size=5,
        location=(center_x, center_y, min_z)
    )

    # SETUP STUDIO LIGHTING
    rim_data = bpy.data.lights.new(name="RimLight", type="SUN")
    rim_obj = bpy.data.objects.new(name="RimLight", object_data=rim_data)
    bpy.context.collection.objects.link(rim_obj)

    # Position and rotate behind the object (adjust these values as needed)
    rim_obj.rotation_euler = Euler((math.radians(-40), math.radians(0), math.radians(0)), "XYZ")
    rim_data.energy = 3  
    rim_data.color = (0.8, 0.9, 1.0)  # Cool blue-white tint


    rim_data = bpy.data.lights.new(name="RimLight3", type="SUN")
    rim_obj = bpy.data.objects.new(name="RimLight3", object_data=rim_data)
    bpy.context.collection.objects.link(rim_obj)

    # Position and rotate behind the object (adjust these values as needed)
    rim_obj.rotation_euler = Euler((math.radians(0), math.radians(60), math.radians(-30)), "XYZ")
    rim_data.energy = 2  
    rim_data.color = (0.8, 0.9, 1.0)  # Cool blue-white tint


    rim_data = bpy.data.lights.new(name="RimLight4", type="SUN")
    rim_obj = bpy.data.objects.new(name="RimLight4", object_data=rim_data)
    bpy.context.collection.objects.link(rim_obj)

    # Position and rotate behind the object (adjust these values as needed)
    rim_obj.rotation_euler = Euler((math.radians(0), math.radians(-60), math.radians(30)), "XYZ")
    rim_data.energy = 2  
    rim_data.color = (0.8, 0.9, 1.0)  # Cool blue-white tint

    return mesh_obj


if __name__ == "__main__":
    black_leather = Material(
        diffuse=r"C:\Users\josephd\Pictures\textures\FabricLeatherCowhide001\FabricLeatherCowhide001_COL_VAR1_4K.jpg",
        scale= 3.0,
    )

    tan_leather = Material(
        diffuse=r"C:\Users\josephd\Pictures\textures\FabricLeatherCowhide001\FabricLeatherCowhide001_COL_VAR3_4K.jpg",
        scale=3.0
    )

    white_fabric = Material(
        diffuse=r"C:\Users\josephd\Pictures\textures\Fabric062_4K-JPG\Fabric062_4K-JPG_Color.jpg",
        roughness=r"C:\Users\josephd\Pictures\textures\Fabric062_4K-JPG\Fabric062_4K-JPG_Roughness.jpg",
        scale=7.0
    )

    wood = Material(
        diffuse=r"C:\Users\josephd\Pictures\textures\Poliigon_WoodVeneerOak_7760\Poliigon_WoodVeneerOak_7760_BaseColor.jpg",
        roughness=r"C:\Users\josephd\Pictures\textures\Poliigon_WoodVeneerOak_7760\Poliigon_WoodVeneerOak_7760_Roughness.jpg",
        normal=r"C:\Users\josephd\Pictures\textures\Poliigon_WoodVeneerOak_7760\Poliigon_WoodVeneerOak_7760_Normal.png"
    )

    materials = {
        "primary": [black_leather, tan_leather, white_fabric],
        "secondary": [wood],
        "tertiary": [],
    }

    obj = setup_scene(model_path=r"C:\Users\josephd\Pictures\furniture\32-view-sofa\grouped.glb")
    print("Finished scene setup, starting to apply and bake")
    permutate_and_bake_materials(materials=materials, obj=obj, bake_dir=r"C:\Users\josephd\Pictures\furniture\32-view-sofa\baked_textures")