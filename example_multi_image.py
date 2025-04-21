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


def remove_all_backgrounds(images):

    # Process each image to remove the background
    for i, image in enumerate(images):
        input_array = np.array(image)
        # Remove the background
        output = rembg.remove(input_array)
        # Save the output image
        images[i] = Image.fromarray(output)

    return images


def trellis_multiple_images(images, output_dir):
    os.makedirs(output_dir, exist_ok=True)
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
            "steps": 10,
            "cfg_strength": 7.5,
        },
        slat_sampler_params={
            "steps": 10,
            "cfg_strength": 3,
        },
    )

    torch.cuda.empty_cache()
    # outputs is a dictionary containing generated 3D assets in different formats:
    # - outputs['gaussian']: a list of 3D Gaussians
    # - outputs['radiance_field']: a list of radiance fields
    # - outputs['mesh']: a list of meshes

    video_gs = render_utils.render_video(outputs['gaussian'][0])['color']
    torch.cuda.empty_cache()
    video_mesh = render_utils.render_video(outputs['mesh'][0])['normal']
    torch.cuda.empty_cache()
    video = [np.concatenate([frame_gs, frame_mesh], axis=1) for frame_gs, frame_mesh in zip(video_gs, video_mesh)]
    imageio.mimsave(os.path.join(output_dir, "video.mp4"), video, fps=30)

    torch.cuda.empty_cache()

    # GLB files can be extracted from the outputs
    glb = postprocessing_utils.to_glb(
        outputs['gaussian'][0],
        outputs['mesh'][0],
        # Optional parameters
        simplify=0.95,          # Ratio of triangles to remove in the simplification process
        texture_size=1024,      # Size of the texture used for the GLB
    )
    glb.export(os.path.join(output_dir, "model.glb"))


def process_and_export_glb(input_path: str, output_path: str, merge_distance: float = 0.001):
    """
    Imports a GLB file, merges all mesh vertices by distance,
    performs a Smart UV project, and exports the mesh as a GLB.

    Parameters:
        input_path (str): File path to the input GLB.
        output_path (str): File path for the exported GLB.
        merge_distance (float): Distance threshold for merging vertices.
    """

    if not os.path.exists(input_path):
        raise RuntimeError(f"Input file not found: {input_path}")

    # Clear the current scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # Import the GLB
    bpy.ops.import_scene.gltf(filepath=input_path)

    # Collect imported mesh objects
    meshes = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']
    if not meshes:
        print("No mesh objects were imported.")
        return

    # If multiple meshes were imported, join them into a single object
    if len(meshes) > 1:
        bpy.ops.object.select_all(action='DESELECT')
        for obj in meshes:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = meshes[0]
        bpy.ops.object.join()
        merged_obj = bpy.context.view_layer.objects.active
    else:
        merged_obj = meshes[0]
        merged_obj.select_set(True)

    # Enter Edit mode, select all vertices, and merge them by distance
    # Set the active object to your merged mesh
    bpy.context.view_layer.objects.active = merged_obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.0001)
    bpy.ops.uv.smart_project()
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')

    # Export the processed mesh as GLB
    bpy.ops.export_scene.gltf(filepath=output_path, export_format='GLB')
    print(f"Exported processed GLB to {output_path}")


if __name__ == "__main__":
    output_dir = "./"
    # Load an image
    images = [
        Image.open("C:/Users/josephd/Pictures/furniture/salema2/views/back.jpg"),
        Image.open("C:/Users/josephd/Pictures/furniture/salema2/views/front.jpg"),
        Image.open("C:/Users/josephd/Pictures/furniture/salema2/views/three-quarters.jpg"),
    ]
    trellis_multiple_images(images, output_dir)
    process_and_export_glb(os.path.join(output_dir, "model.glb"), os.path.join(output_dir, "model_processed.glb"))