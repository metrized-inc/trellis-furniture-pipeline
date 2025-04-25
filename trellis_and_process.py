from example_multi_image import trellis_multiple_images
import os
from PIL import Image
import click


@click.command()
@click.option('--image_folder', type=str, help='Path to the folder containing images.')
# @click.option('--output_folder', type=str, default=os.path.join(image_folder, "trellis_out", "model_processed.obj"), help='Path to the output folder.')


def process_images(image_folder):
    imgs = []
    valid_images = [".jpeg", ".jpg",".png"]
    for f in os.listdir(image_folder):
        ext = os.path.splitext(f)[1]
        if ext.lower() not in valid_images:
            continue
        imgs.append(Image.open(os.path.join(image_folder,f)))

    print(f"Found {len(imgs)} images in {image_folder}.")
    data = trellis_multiple_images(imgs)

    output_file = os.path.join(image_folder, "trellis_out", "model_processed.obj")
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "wb") as f:
        f.write(data)
    

if __name__ == "__main__":
    process_images()