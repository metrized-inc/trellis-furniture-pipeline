import bpy
from pathlib import Path
import math
from mathutils import Euler, Vector


def compute_camera_distance_to_fit_object(obj, camera, margin=1.2):
    bbox = [Vector(b) for b in obj.bound_box]
    dimensions = max((v - bbox[0]).length for v in bbox)
    cam_data = camera.data
    scene = bpy.context.scene
    aspect = scene.render.resolution_x / scene.render.resolution_y
    fov = cam_data.angle if aspect >= 1 else cam_data.angle / aspect
    distance = (dimensions * margin) / (2 * math.tan(fov / 2))
    return distance



def setup_camera_and_render_views(output_dir: Path, model_path: Path):
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

        # # Optional: Add second rim light for symmetry
        # rim_data2 = bpy.data.lights.new(name="RimLight2", type="SUN")
        # rim_obj2 = bpy.data.objects.new(name="RimLight2", object_data=rim_data2)
        # bpy.context.collection.objects.link(rim_obj2)
        # rim_obj2.rotation_euler = Euler(
        #     (math.radians(110), math.radians(140), 200), "XYZ"
        # )
        # rim_data2.energy = 3.0
        # rim_data2.color = (0.8, 0.9, 1.0)


    # Add opposing light (SUN) to illuminate the opposite side
    if "OpposingLight" not in bpy.data.objects:
        opposing_light_data = bpy.data.lights.new(name="OpposingLight", type="SUN")
        opposing_light_obj = bpy.data.objects.new(name="OpposingLight", object_data=opposing_light_data)
        bpy.context.collection.objects.link(opposing_light_obj)

        opposing_light_obj.rotation_euler = Euler((math.radians(110), math.radians(140), 90), "XYZ")
        opposing_light_data.energy = 40
        opposing_light_data.color = (0.8, 0.9, 1.0)

        # opposing_light_data2 = bpy.data.lights.new(name="OpposingLight2", type="SUN")
        # opposing_light_obj2 = bpy.data.objects.new(name="OpposingLight2", object_data=opposing_light_data2)
        # bpy.context.collection.objects.link(opposing_light_obj2)
        
        # opposing_light_obj2.rotation_euler = Euler((math.radians(110), math.radians(90), 270), "XYZ")
        # opposing_light_data2.energy = 40
        # opposing_light_data2.color = (0.8, 0.9, 1.0)

    
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


if __name__ == "__main__":
    model_path = Path("model.glb")

    render_output_path = Path("C:/Users/josephd/Pictures/furniture/salema2/renderings")
    setup_camera_and_render_views(render_output_path, model_path)
