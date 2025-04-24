import gradio as gr

from example_multi_image import trellis_multiple_images
from retex_and_bake import setup_hdri_environment, permutate_and_bake_materials, Material



def texturepipe(model_file):
    model_path = model_file.name
    hdri="hdris\studio_small_09_1k.exr"
    hdri=r"C:\Users\josephd\Pictures\textures\HDRIs\studio_small_09_1k.exr"
    strength=1.4

    wood = Material(
        diffuse=r"C:\Users\josephd\Pictures\textures\Poliigon_WoodVeneerOak_7760\Poliigon_WoodVeneerOak_7760_BaseColor.jpg",
        roughness=r"C:\Users\josephd\Pictures\textures\Poliigon_WoodVeneerOak_7760\Poliigon_WoodVeneerOak_7760_Roughness.jpg",
        normal=r"C:\Users\josephd\Pictures\textures\Poliigon_WoodVeneerOak_7760\Poliigon_WoodVeneerOak_7760_Normal.png"
    )

    alma_forest_green = Material(
        diffuse=r"C:\Users\josephd\Pictures\textures\bird_couches\Alma Forest Green\0a23297c-2415-402b-8944-a2f01f59c53d.png",
        orm=r"C:\Users\josephd\Pictures\textures\bird_couches\Alma Forest Green\orm_map.png"
    )

    materials = {
        "primary": [alma_forest_green],
        "secondary": [wood],
        "tertiary": [],
    }

    obj = setup_hdri_environment(model_path, hdri, strength)
    return permutate_and_bake_materials(materials, obj)
    


TRELLIS = gr.Interface(fn=trellis_multiple_images, 
                       inputs=gr.Gallery(type="pil", label="Input Images"), 
                       outputs="file", title="TRELLIS", description="Upload images to process with TRELLIS.")

TEXTURE = gr.Interface(
    fn=texturepipe,
    inputs=gr.File(label="Upload model (GLB)"),
    outputs=gr.Gallery(type="pil"),
    title="RETEX",
    description="Upload a model to be retextured."
)

demo = gr.TabbedInterface([TRELLIS, TEXTURE], ["TRELLIS", "RETEX"])
demo.launch()