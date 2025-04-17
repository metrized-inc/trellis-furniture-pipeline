import bpy
from pathlib import Path
import math
from mathutils import Euler, Vector
import os
from PIL import Image


def project_texture_from_camera(obj, cam_obj, proj_image_filepath, blend_factor=1.0):
    """
    Projects a new image onto the object's current texture by blending the projected image
    (using the camera's perspective via a UV Project modifier) with the existing base texture.
    
    Parameters:
        obj (bpy.types.Object): The target mesh object.
        cam_obj (bpy.types.Object): The camera to use for the projection.
        proj_image_filepath (str): The file path to the image to project.
        blend_factor (float): Factor for mixing (0 means only original texture, 1 means only projected image).
    """

    # --- Load the projection image ---
    proj_image_filepath = str(Path(proj_image_filepath).resolve())
    proj_image = None
    for img in bpy.data.images:
        if Path(img.filepath).resolve().as_posix() == Path(proj_image_filepath).as_posix():
            proj_image = img
            break
    if not proj_image:
        try:
            proj_image = bpy.data.images.load(proj_image_filepath)
        except Exception as e:
            print(f"Failed to load projection image {proj_image_filepath}: {e}")
            return

    # --- Ensure a separate UV map exists for projection: "ProjUV" ---
    uv_map_name = "ProjUV"
    if uv_map_name not in obj.data.uv_layers:
        obj.data.uv_layers.new(name=uv_map_name)
    # Note: The active UV map is not automatically set; we'll instruct the modifier which one to use.

    # --- Add a UV Project modifier for the projection ---
    mod_name = "UVProject_Proj"
    if mod_name in obj.modifiers:
        uv_project = obj.modifiers[mod_name]
    else:
        uv_project = obj.modifiers.new(name=mod_name, type='UV_PROJECT')
    uv_project.uv_layer = uv_map_name
    uv_project.projectors.clear()
    proj = uv_project.projectors.new()
    proj.object = cam_obj

    # --- Update the object's material node tree ---
    # Assume the object already has a material. Use the first material.
    if not obj.data.materials:
        print("Object has no material; cannot project onto existing texture.")
        return
    mat = obj.data.materials[0]
    if not mat.use_nodes:
        mat.use_nodes = True
    nt = mat.node_tree

    # Get the Principled BSDF node (create it if missing)
    bsdf = nt.nodes.get("Principled BSDF")
    if not bsdf:
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")

    # Find the node currently feeding the Base Color (if any)
    base_color_input = bsdf.inputs["Base Color"]
    original_link = base_color_input.links[0].from_node if base_color_input.links else None

    # Create a new Image Texture node for the projected image
    proj_img_node = nt.nodes.new("ShaderNodeTexImage")
    proj_img_node.image = proj_image
    proj_img_node.label = "Projected Image"

    # Create a UV Map node to force use of our "ProjUV" UV layer
    uv_map_node = nt.nodes.new("ShaderNodeUVMap")
    uv_map_node.uv_map = uv_map_name

    # Connect the UV Map node to the Vector input of the projected image node
    nt.links.new(uv_map_node.outputs["UV"], proj_img_node.inputs["Vector"])

    # Create (or reuse) a MixRGB node to blend the original texture with the new projection.
    # Try to find an existing MixRGB node labeled "TextureBlend"
    mix_node = None
    for node in nt.nodes:
        if node.type == "MIX_RGB" and node.label == "TextureBlend":
            mix_node = node
            break
    if not mix_node:
        mix_node = nt.nodes.new("ShaderNodeMixRGB")
        mix_node.label = "TextureBlend"
        mix_node.blend_type = "MIX"
        mix_node.inputs["Fac"].default_value = blend_factor

    # Set up the mix factors
    mix_node.inputs[0].default_value = blend_factor  # Factor input
    # Connect the existing texture (if any) to MixRGB Color1, else use white if missing
    if original_link:
        nt.links.new(original_link.outputs[0], mix_node.inputs[1])
    else:
        mix_node.inputs[1].default_value = (1.0, 1.0, 1.0, 1.0)
    # Connect the projected image to MixRGB Color2
    nt.links.new(proj_img_node.outputs["Color"], mix_node.inputs[2])

    # Re-route the MixRGB node output to the BSDF Base Color.
    # First, remove any existing links from Base Color
    while base_color_input.links:
        nt.links.remove(base_color_input.links[0])
    nt.links.new(mix_node.outputs["Color"], base_color_input)

    print(f"Projected image '{proj_image_filepath}' blended (factor={blend_factor}) with object's current texture using camera '{cam_obj.name}'.")


def bake_projection_step(obj, bake_width=1024, bake_height=1024, bake_image_name="BakeImage"):
    """
    Bakes the current material’s Base Color into a new image and then reconnects it as the new base texture.
    This clears out the temporary projection nodes so that they are baked into the texture.
    """
    import bpy
    
    mat = obj.data.materials[0]
    nt = mat.node_tree

    # Create (or get) an image texture node dedicated for baking.
    bake_node = nt.nodes.get("BakeImage")
    if not bake_node:
        bake_node = nt.nodes.new("ShaderNodeTexImage")
        bake_node.name = "BakeImage"
        bake_node.label = "BakeImage"
        # Position it (optional)
        bake_node.location = (-400, 0)

    # Create a new image for baking.
    bake_img = bpy.data.images.new(bake_image_name, width=bake_width, height=bake_height, alpha=True)
    bake_node.image = bake_img

    # Set the BakeImage node as the active node.
    nt.nodes.active = bake_node

    # Switch to Cycles for baking.
    previous_engine = bpy.context.scene.render.engine
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.bake_type = 'COMBINED'
    bpy.context.scene.render.bake.use_clear = True

    # Make sure the object is active.
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    
    # Bake. (This may bring up a progress bar in the UI.)
    bpy.ops.object.bake('INVOKE_DEFAULT')

    # After baking, remove all nodes except for the Principled BSDF and our bake node.
    # For simplicity, we will remove all links from the Base Color input and reconnect the bake image.
    bsdf = nt.nodes.get("Principled BSDF")
    if bsdf:
        base_color_input = bsdf.inputs["Base Color"]
        # Remove existing links.
        while base_color_input.links:
            nt.links.remove(base_color_input.links[0])
        # Create a link from the baked image.
        nt.links.new(bake_node.outputs["Color"], base_color_input)
    
    # Clean up: remove projection nodes if desired.
    # (You might choose to remove nodes labeled "Projected Image", "TextureBlend", "UVMap", etc.)
    for node in list(nt.nodes):
        if node.name.startswith("Projected Image") or node.name.startswith("TextureBlend") or node.type == "UVMap":
            nt.nodes.remove(node)
    
    # Switch back to the previous render engine.
    bpy.context.scene.render.engine = previous_engine
    print(f"Baked projection into image '{bake_image_name}'.")


def project_all_textures_from_camera(obj, cam_obj, views, images, blend_factor=0.5):
    """
    For each view, projects an image onto the object's texture, then bakes the result into the texture.
    This way each projection becomes part of the base texture before the next is applied.
    """
    import bpy, os
    i = 0
    for view_name, location in views.items():
        # Position the camera.
        cam_obj.location = location
        bpy.context.view_layer.update()
        # Apply projection from current view.
        project_texture_from_camera(obj, cam_obj, images[i], blend_factor)
        # Bake the projection into a new base texture.
        bake_projection_step(obj, bake_image_name=f"Bake_{view_name}")
        i += 1


def compute_camera_distance_to_fit_object(obj, camera, margin=1.2):
    bbox = [Vector(b) for b in obj.bound_box]
    dimensions = max((v - bbox[0]).length for v in bbox)
    cam_data = camera.data
    scene = bpy.context.scene
    aspect = scene.render.resolution_x / scene.render.resolution_y
    fov = cam_data.angle if aspect >= 1 else cam_data.angle / aspect
    distance = (dimensions * margin) / (2 * math.tan(fov / 2))
    return distance



def setup_camera_and_render_views(output_dir: Path, model_path: Path, image_folder: Path):
    output_dir.mkdir(parents=True, exist_ok=True)

    # Turn on GPU ray tracing
    bpy.context.scene.render.engine = "BLENDER_EEVEE"
    bpy.context.scene.cycles.device = "GPU"  # Optional: use GPU if available
    bpy.context.scene.cycles.use_adaptive_sampling = (
        True  # More samples in detailed areas
    )
    bpy.context.scene.cycles.use_denoising = True  # Reduce noise after sampling
    bpy.context.scene.cycles.samples = 2048  # good baseline

    bpy.data.objects['Cube'].select_set(True)  # Only delete the cube
    bpy.ops.object.delete()  # Delete selected objects

    bpy.ops.import_scene.gltf(filepath=str(model_path))
    imported_objects = list(bpy.context.selected_objects)
    imported_mesh = next((obj for obj in imported_objects if obj.type == 'MESH'), None)

    # Apply smooth shading after import
    for obj in bpy.context.selected_objects:
        if obj.type == 'MESH':
            for face in obj.data.polygons:
                face.use_smooth = True

    # Render white background
    world = bpy.context.scene.world
    if not world:
        world = bpy.data.worlds.new("World")
        bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (1, 1, 1, 1)
    bpy.context.scene.view_settings.view_transform = "Standard"
    # End render white

    cam_data = bpy.data.cameras.new("RenderCam")
    cam_obj = bpy.data.objects.new("RenderCam", cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj

    cam_data.clip_start = 0.01
    cam_data.clip_end = 1000

    bpy.context.scene.render.image_settings.file_format = "PNG"
    bpy.context.scene.render.resolution_x = 1920
    bpy.context.scene.render.resolution_y = 1080
    bpy.context.scene.render.resolution_percentage = 100
    bpy.context.scene.render.film_transparent = False

    # Rim lighting
    # Add rim light (SUN type works best for directional edge lighting)
    if "RimLight" not in bpy.data.objects:
        rim_data = bpy.data.lights.new(name="RimLight", type="SUN")
        rim_obj = bpy.data.objects.new(name="RimLight", object_data=rim_data)
        bpy.context.collection.objects.link(rim_obj)

        # Position and rotate behind the object (adjust these values as needed)
        rim_obj.rotation_euler = Euler((math.radians(110), math.radians(140), 270), "XYZ")
        rim_data.energy = 40  
        rim_data.color = (0.8, 0.9, 1.0)  # Cool blue-white tint


    # Add opposing light (SUN) to illuminate the opposite side
    if "OpposingLight" not in bpy.data.objects:
        opposing_light_data = bpy.data.lights.new(name="OpposingLight", type="SUN")
        opposing_light_obj = bpy.data.objects.new(name="OpposingLight", object_data=opposing_light_data)
        bpy.context.collection.objects.link(opposing_light_obj)

        opposing_light_obj.rotation_euler = Euler((math.radians(110), math.radians(140), 90), "XYZ")
        opposing_light_data.energy = 40
        opposing_light_data.color = (0.8, 0.9, 1.0)

    
    target_obj = next(
        (obj for obj in bpy.context.scene.objects if obj.type == "MESH"), None
    )
    if not target_obj:
        raise RuntimeError("No mesh object found.")

    # Object tracking
    # -------------------------------------------------
    # 🧭 Add Empty Target at Object Center for "Track To"
    # -------------------------------------------------
    # Move origin to geometry center just in case
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = target_obj
    target_obj.select_set(True)
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")

    # Create an empty at object's origin
    empty_target = bpy.data.objects.new("RenderTarget", None)
    empty_target.location = target_obj.location
    bpy.context.collection.objects.link(empty_target)

    # Add a 'Track To' constraint to keep camera pointed at model
    track_to = cam_obj.constraints.new(type="TRACK_TO")
    track_to.target = empty_target
    track_to.track_axis = "TRACK_NEGATIVE_Z"
    track_to.up_axis = "UP_Y"

    #

    suggested_distance = compute_camera_distance_to_fit_object(target_obj, cam_obj)
    views = {
        f"view_{angle:03}": (
            math.cos(math.radians(angle)) * suggested_distance,
            math.sin(math.radians(angle)) * suggested_distance,
            suggested_distance * 0.2,  # Keep camera flat on Z axis
        )
        for angle in range(0, 360, 45)
    }

    for view_name, location in views.items():
        # cam_obj.rotation_euler = rotation
        cam_obj.location = location
        bpy.context.view_layer.update()

        filepath = (output_dir / f"{view_name}.png").resolve()
        bpy.context.scene.render.filepath = str(filepath)
        bpy.ops.render.render(write_still=True)
        print(f" Saved: {filepath}")

    
    imgs = []
    valid_images = [".jpeg", ".jpg",".gif",".png",".tga"]
    for f in os.listdir(image_folder):
        ext = os.path.splitext(f)[1]
        if ext.lower() not in valid_images:
            continue
        imgs.append(os.path.join(image_folder,f))
    
    project_all_textures_from_camera(imported_mesh, cam_obj, views, imgs)


    for view_name, location in views.items():
        # cam_obj.rotation_euler = rotation
        cam_obj.location = location
        bpy.context.view_layer.update()

        filepath = (output_dir / f"{view_name}-retextured.png").resolve()
        bpy.context.scene.render.filepath = str(filepath)
        bpy.ops.render.render(write_still=True)
        print(f" Saved: {filepath}")


if __name__ == "__main__":
    model_path = Path("model.glb")
    image_folder = Path(r"C:\Users\josephd\Pictures\furniture\salema2\retextured")

    render_output_path = Path("C:/Users/josephd/Pictures/furniture/salema2/renderings")
    setup_camera_and_render_views(render_output_path, model_path, image_folder)
