from example_multi_image import trellis_multiple_images, process_and_export_glb
# from normal_render import setup_camera_and_render_views
import os
from PIL import Image
# from pathlib import Path


if __name__ == "__main__":
    image_folder = r"C:\Users\josephd\Pictures\furniture\sample couch sections\30225-06\source"
    imgs = []
    valid_images = [".jpeg", ".jpg",".png"]
    for f in os.listdir(image_folder):
        ext = os.path.splitext(f)[1]
        if ext.lower() not in valid_images:
            continue
        imgs.append(Image.open(os.path.join(image_folder,f)))

    data = trellis_multiple_images(imgs)
    with open(os.path.join(image_folder, "trellis_out", "model_processed.obj"), "wb") as f:
        f.write(data)
    # trellis_and_process(r"C:\Users\josephd\Pictures\furniture\sample couch sections\30225-10\source")