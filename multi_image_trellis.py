import os
import torch
import bpy
# os.environ['ATTN_BACKEND'] = 'xformers'   # Can be 'flash-attn' or 'xformers', default is 'flash-attn'
os.environ['SPCONV_ALGO'] = 'native'        # Can be 'native' or 'auto', default is 'auto'.
                                            # 'auto' is faster but will do benchmarking at the beginning.
                                            # Recommended to set to 'native' if run only once.

import numpy as np
import imageio
from PIL import Image
from trellis.pipelines import TrellisImageTo3DPipeline
from trellis.utils import render_utils, postprocessing_utils
import rembg
from utils import import_glb_merge_vertices


def remove_all_backgrounds(images):

    # Process each image to remove the background
    for i, image in enumerate(images):
        # Take first item from gradio tuple
        if isinstance(image, tuple):
            image = image[0]

        input_array = np.array(image)
        # Remove the background
        output = rembg.remove(input_array)
        # Save the output image
        images[i] = Image.fromarray(output)

    return images


def trellis_multiple_images(images):
    # Load a pipeline from a model folder or a Hugging Face model hub.
    pipeline = TrellisImageTo3DPipeline.from_pretrained("JeffreyXiang/TRELLIS-image-large")
    pipeline.cuda()

    images = remove_all_backgrounds(images)

    torch.cuda.empty_cache()

    # Run the pipeline
    outputs = pipeline.run_multi_image(
        images,
        seed=1,
        # Optional parameters
        sparse_structure_sampler_params={
            "steps": 15,
            "cfg_strength": 16,
        },
        slat_sampler_params={
            "steps": 15,
            "cfg_strength": 3,
        },
    )

    torch.cuda.empty_cache()
    # outputs is a dictionary containing generated 3D assets in different formats:
    # - outputs['gaussian']: a list of 3D Gaussians
    # - outputs['radiance_field']: a list of radiance fields
    # - outputs['mesh']: a list of meshes

    # video_gs = render_utils.render_video(outputs['gaussian'][0])['color']
    # torch.cuda.empty_cache()
    # video_mesh = render_utils.render_video(outputs['mesh'][0])['normal']
    # torch.cuda.empty_cache()
    # video = [np.concatenate([frame_gs, frame_mesh], axis=1) for frame_gs, frame_mesh in zip(video_gs, video_mesh)]
    # imageio.mimsave(os.path.join(output_dir, "video.mp4"), video, fps=30)

    torch.cuda.empty_cache()

    # GLB files can be extracted from the outputs
    glb = postprocessing_utils.to_glb(
        outputs['gaussian'][0],
        outputs['mesh'][0],
        # Optional parameters
        simplify=0.95,          # Ratio of triangles to remove in the simplification process
        texture_size=1024,      # Size of the texture used for the GLB
    )
    glb.export(os.path.join("tmp", "model.glb"))
    return process_and_export_obj(os.path.join("tmp", "model.glb"))


def process_and_export_obj(input_path: str):
    """
    Imports a GLB file, merges all mesh vertices by distance,
    performs a Smart UV project, and exports the mesh as a OBJ.

    Parameters:
        input_path (str): File path to the input GLB.
        output_path (str): File path for the exported OBJ.
        merge_distance (float): Distance threshold for merging vertices.
    """

    if not os.path.exists(input_path):
        raise RuntimeError(f"Input file not found: {input_path}")

    # Clear the current scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # Import the GLB
    merged_obj = import_glb_merge_vertices(input_path)

    bpy.context.view_layer.objects.active = merged_obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project()
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')

    # Add one iteration of subdivision surface before UV unwrapping
    subdiv = merged_obj.modifiers.new(name="Subdivision", type='SUBSURF')
    subdiv.levels = 1
    subdiv.render_levels = 1
    # Apply the modifier so the subdivision becomes part of the mesh geometry
    bpy.ops.object.modifier_apply(modifier="Subdivision")

    # Set shading to smooth for all polygons
    for poly in merged_obj.data.polygons:
        poly.use_smooth = True

    # Export the processed mesh as OBJ
    temp_path = os.path.join("tmp", "model_processed.obj")
    bpy.ops.wm.obj_export(filepath=temp_path)

    with open(temp_path, "rb") as f:
        obj_data = f.read()
    return obj_data


if __name__ == "__main__":
    # output_dir = "./"
    # # Load an image
    # images = [
    #     Image.open("C:/Users/josephd/Pictures/furniture/salema2/views/back.jpg"),
    #     Image.open("C:/Users/josephd/Pictures/furniture/salema2/views/front.jpg"),
    #     Image.open("C:/Users/josephd/Pictures/furniture/salema2/views/three-quarters.jpg"),
    # ]
    # data = trellis_multiple_images(images)
    # with open(os.path.join(output_dir, "model_processed.obj"), "wb") as f:
    #     f.write(data)
    process_and_export_obj(os.path.join("tmp", "model.glb"))
    # process_and_export_obj(r"C:\Users\josephd\Pictures\furniture\sample couch sections\30225-10\trellis_out\model.glb")