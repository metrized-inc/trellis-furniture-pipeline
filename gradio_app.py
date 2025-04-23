import gradio as gr

from example_multi_image import trellis_multiple_images
from retex_and_bake import setup_hdri_environment, permutate_and_bake_materials



def texturepipe(subject):
    hdri="hdris\studio_small_09_1k.exr"
    strength=1.4
    pass


TRELLIS = gr.Interface(fn=trellis_multiple_images, 
                       inputs=gr.Gallery(type="pil", label="Input Images"), 
                       outputs="file", title="TRELLIS", description="Upload images to process with TRELLIS.")

TEXTURE = gr.Interface(fn=texturepipe, inputs="text", outputs="text", title="RETEX", description="Upload a model to be retextured.")

demo = gr.TabbedInterface([TRELLIS, TEXTURE], ["TRELLIS", "RETEX"])
demo.launch()