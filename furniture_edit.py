import torch
from diffusers import (
    StableDiffusionXLInstructPix2PixPipeline,
    StableDiffusionXLAdapterPipeline,
    StableDiffusionXLImg2ImgPipeline,
    EDMEulerScheduler,
)
from diffusers.utils import load_image
from PIL import Image


def main(input, texture, out, item, strength=0.4, guidance=7.0, ip_scale=0.7, steps=30):
    negative = "blurry, low resolution, lowres, noisy, grainy, washed out, overexposed, underexposed, flat lighting, harsh shadows, fake shadows, cartoon, anime, illustration, painting, abstract, smooth plastic texture, waxy, extra limbs, distorted geometry, broken chair, unrealistic lighting, color banding, messy fabric, fake reflections, glowing edges, poor depth of field, incorrect focus, warped perspective, unnatural folds, AI artifacts, double exposure, image glitches"
    prompt = f'A photorealistic image of a {item}, photorealistic upholstery, natural fabric folds, realistic shadows and lighting, studio lighting with soft shadows, ambient occlusion, high detail rendering, shallow depth of field, shot with a DSLR, subtle reflections on the fabric surface. The brackground is completely white.'
    device = "cuda" if torch.cuda.is_available() else "cpu"

    # ---- 1. get the CosXL‑Edit checkpoint -----------------------------------
    ckpt_path = r"C:\Users\josephd\Documents\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable\ComfyUI\models\checkpoints\cosxl_edit.safetensors"
    
    pipe = StableDiffusionXLImg2ImgPipeline.from_single_file(
        ckpt_path,
        num_in_channels=8,          # required for edit models
        is_cosxl_edit=True,         # tells diffusers to apply CosXL scaling rules
        torch_dtype=torch.float16,
    )

    # CosXL uses the cosine‑continuous EDM V‑prediction scheduler
    pipe.scheduler = EDMEulerScheduler(
        sigma_min=0.002, sigma_max=120.0, sigma_data=1.0,
        prediction_type="v_prediction", sigma_schedule="exponential"
    )
    pipe.to(device)

    # ---- 2. attach an IP‑Adapter so we can pass a texture image ------------
    # The vanilla SDXL IP‑Adapter weights share the same CLIP‑ViT‑bigG image encoder
    pipe.load_ip_adapter(
        "h94/IP-Adapter",                # repo
        subfolder="sdxl_models",
        weight_name="ip-adapter_sdxl.bin"
    )
    pipe.set_ip_adapter_scale(ip_scale)   # how strongly to follow the texture

    # ---- 3. load user assets ----------------------------------------------
    base_image   = load_image(input).convert("RGB")
    texture_img  = load_image(texture).convert("RGB")

    # optional resize to keep VRAM under control
    base_image   = base_image.resize((1024, 1024), Image.Resampling.LANCZOS)
    texture_img  = texture_img.resize((512, 512),  Image.Resampling.LANCZOS)

    # ---- 4. run the edit ---------------------------------------------------
    edited = pipe(
        prompt=prompt,
        negative_prompt=negative,
        image=base_image,                 # the picture we’re editing
        ip_adapter_image=texture_img,     # texture / style guide
        strength=strength,           # 0 = no change, 1 = ignore original
        guidance_scale=guidance,
        num_inference_steps=steps,
    ).images[0]

    edited.save(out)
    print("✅ Saved:", out)

if __name__ == "__main__":
    texture = r"C:\Users\josephd\Pictures\textures\grey_fabric.png"
    input = r"C:\Users\josephd\Pictures\furniture\salema2\renderings\view_000.png"
    out = r"C:\Users\josephd\Pictures\furniture\salema2\edited\view_000.png"
    item = "couch"
    main(input, texture, out, item)