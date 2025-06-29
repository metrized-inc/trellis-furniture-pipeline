import bpy
import os
import math
from utils import import_glb_merge_vertices


# returns a list of the paths to the output images
def model_to_views(model_path, output_path, num_views=4):
    if not os.path.exists(model_path):
        raise RuntimeError(f"Input file not found: {model_path}")

    scn = bpy.context.scene

    scn.render.image_settings.file_format = 'PNG'

    scn.render.resolution_x = 1080
    scn.render.resolution_y = 1080

    # create the first camera
    cam1 = bpy.data.cameras.new("Camera 1")
    cam1.lens = 90

    # create the first camera object
    cam_obj1 = bpy.data.objects.new("Camera 1", cam1)
    cam_obj1.location = (0, -3.5, 0.4)
    cam_obj1.rotation_euler = (math.radians(85), 0, 0)
    # scn.collection.objects.link(cam_obj1)

    scn.camera = cam_obj1

    # Change background color of world
    bpy.data.worlds["World"].node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)

    merged_obj = import_glb_merge_vertices(model_path)

    if merged_obj.name not in [obj.name for obj in scn.collection.objects]:
        scn.collection.objects.link(merged_obj)
    merged_obj.rotation_mode = 'XYZ'

    merged_obj.select_set(True)
                          
    bpy.ops.view3d.camera_to_view_selected()

    cam1.lens = 45

    angle_delta = 360 / num_views
    paths = []
    angle = 0.0
    while angle < 360:
        merged_obj.rotation_euler = (0, 0, math.radians(angle))
        bpy.context.view_layer.update()

        path = os.path.join(output_path, f"{angle:.2f}.png")
        paths.append(path)
        scn.render.filepath = path
        bpy.ops.render.render(write_still=True)

        angle += angle_delta
    
    return paths


if __name__ == "__main__":
    model_to_views(r"C:\Users\josephd\Documents\3D Objects\TRELLIS\iq_chair_multi.glb", 
                   os.path.join(os.getcwd(), "tmp"), 
                   4)