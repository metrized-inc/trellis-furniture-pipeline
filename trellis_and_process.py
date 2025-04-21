from example_multi_image import trellis_multiple_images, process_and_export_glb
# from normal_render import setup_camera_and_render_views
import os
from PIL import Image
# from pathlib import Path


def trellis_and_process(image_folder, model_folder=None, output_folder=None):
    imgs = []
    valid_images = [".jpeg", ".jpg",".png"]
    for f in os.listdir(image_folder):
        ext = os.path.splitext(f)[1]
        if ext.lower() not in valid_images:
            continue
        imgs.append(Image.open(os.path.join(image_folder,f)))

    # Run the Trellis pipeline on the loaded images
    if  model_folder is None:
        model_folder = os.path.join(os.path.dirname(image_folder), "trellis_outputs")
    if output_folder is None:
        output_folder = os.path.join(os.path.dirname(image_folder), "renderings")

    trellis_multiple_images(imgs, model_folder)
    process_and_export_glb(os.path.join(model_folder, "model.glb"), os.path.join(model_folder, "model_processed.glb"))
    # setup_camera_and_render_views(Path(output_folder), Path(os.path.join(model_folder, "model.glb")))


if __name__ == "__main__":
    trellis_and_process("C:/Users/josephd/Pictures/furniture/office chair/source")