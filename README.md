<img src="assets/logo.webp" width="100%" align="center">
<h1 align="center">Structured 3D Latents<br>for Scalable and Versatile 3D Generation</h1>
<p align="center"><a href="https://arxiv.org/abs/2412.01506"><img src='https://img.shields.io/badge/arXiv-Paper-red?logo=arxiv&logoColor=white' alt='arXiv'></a>
<a href='https://trellis3d.github.io'><img src='https://img.shields.io/badge/Project_Page-Website-green?logo=googlechrome&logoColor=white' alt='Project Page'></a>
<a href='https://huggingface.co/spaces/JeffreyXiang/TRELLIS'><img src='https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Live_Demo-blue'></a>
</p>
<p align="center"><img src="assets/teaser.png" width="100%"></p>

<span style="font-size: 16px; font-weight: 600;">T</span><span style="font-size: 12px; font-weight: 700;">RELLIS</span> is a large 3D asset generation model. It takes in text or image prompts and generates high-quality 3D assets in various formats, such as Radiance Fields, 3D Gaussians, and meshes. The cornerstone of <span style="font-size: 16px; font-weight: 600;">T</span><span style="font-size: 12px; font-weight: 700;">RELLIS</span> is a unified Structured LATent (<span style="font-size: 16px; font-weight: 600;">SL</span><span style="font-size: 12px; font-weight: 700;">AT</span>) representation that allows decoding to different output formats and Rectified Flow Transformers tailored for <span style="font-size: 16px; font-weight: 600;">SL</span><span style="font-size: 12px; font-weight: 700;">AT</span> as the powerful backbones. We provide large-scale pre-trained models with up to 2 billion parameters on a large 3D asset dataset of 500K diverse objects. <span style="font-size: 16px; font-weight: 600;">T</span><span style="font-size: 12px; font-weight: 700;">RELLIS</span> significantly surpasses existing methods, including recent ones at similar scales, and showcases flexible output format selection and local 3D editing capabilities which were not offered by previous models.

<!-- Installation -->
## 📦 Installation

### Prerequisites
- **Hardware**: CUDA Device, has been tested on a RTX 3060, 6GB VRAM
- **Software**:   
  - The [CUDA Toolkit](https://developer.nvidia.com/cuda-toolkit-archive) is needed to compile certain submodules. The code has been tested with CUDA versions 11.8 and 12.2.  This repo use **CUDA 12.4**.
  - The [VS studio 2022](https://visualstudio.microsoft.com/zh-hans/vs/) with C++ compile needs.

  Give unrestricted script access to powershell so venv can work:

- Open an administrator powershell window
- Type `Set-ExecutionPolicy Unrestricted` and answer A
- Close admin powershell window

### Installation Steps
1. Clone the repo:
    ```
    git clone --recurse-submodules https://github.com/metrized-inc/trellis-furniture-pipeline.git
    ```
## MUST HAVE `--recurse-submodules`

2. Install the dependencies:
    powershell run with `1、install-uv-qinglong.ps1` (right click then choose `use powershell run`)
    auto install in one-clik

<!-- Usage -->
## HOW TO USE (do these steps in order)
NOTE: Before running any of the scripts, activate the venv with ".venv/scripts/activate"
**1.TRELLIS PIPELINE**
- This pipeline feeds a folder of images to TRELLIS, and then performs some post processing to remove duplicate verticies and auto-unwrap the UV Map
- To run it, use the command "python trellis_and_proccess.py --image_folder='path/to/your/image/folder'"

**2.MANUAL STEP**
- Take the .obj outputted by trellis and load it into Blender or your preferred 3d software
- Assign different materials to different parts of your object (e.g. you can select the legs of a chair out and assign it to another material)
- Export the object as a .glb
- NOTE: The final step can take in a maximum of 3 materials, it expects them to be named "primary", "secondary", and "tertiary". Only a primary material is needed for the last step to work

**3.RETEXTURE PIPELINE**
- This step requires you to setup a .json file that specifies the materials you want to apply
- It should be formatted in the way shown in material-example.json
- Each material can hold the following properties (each should be an image path), only the first one is needed for it to be a valid material: ["diffuse", "roughness", "metallic", "normal", "orm"]. In addition, you can specify the scale with the "scale" property
- To run the pipeline: "python retex_and_bake.py --material_json='path/to/json' --model_path='path/to/your/model'"
- Here is a full list of the flags you can use (only the first two are required):
  --material_json TEXT    Path to the json file that specifies the materials,
                          look at material-example.json for reference.
  --model_path TEXT       Path to the model file (.glb or .obj).
  --hdri_path TEXT        Path to the HDRI image (.exr).
  --hdri_strength FLOAT   Strength of the HDRI lighting. Default is 1.5.
  --texture_size INTEGER  Size of the texture to bake. Default is 4096.
  --denoise BOOLEAN       Whether to use denoising. Default is False. (Seams
                          will appear if set to True)
  --samples INTEGER       Number of samples for baking. Default is 40.
  --help                  Show this message and exit.

<!-- Dataset -->
## 📚 Dataset

We provide **TRELLIS-500K**, a large-scale dataset containing 500K 3D assets curated from [Objaverse(XL)](https://objaverse.allenai.org/), [ABO](https://amazon-berkeley-objects.s3.amazonaws.com/index.html), [3D-FUTURE](https://tianchi.aliyun.com/specials/promotion/alibaba-3d-future), [HSSD](https://huggingface.co/datasets/hssd/hssd-models), and [Toys4k](https://github.com/rehg-lab/lowshot-shapebias/tree/main/toys4k), filtered based on aesthetic scores. Please refer to the [dataset README](DATASET.md) for more details.

<!-- License -->
## ⚖️ License

TRELLIS models and the majority of the code are licensed under the [MIT License](LICENSE). The following submodules may have different licenses:
- [**diffoctreerast**](https://github.com/JeffreyXiang/diffoctreerast): We developed a CUDA-based real-time differentiable octree renderer for rendering radiance fields as part of this project. This renderer is derived from the [diff-gaussian-rasterization](https://github.com/graphdeco-inria/diff-gaussian-rasterization) project and is available under the [LICENSE](https://github.com/JeffreyXiang/diffoctreerast/blob/master/LICENSE).


- [**Modified Flexicubes**](https://github.com/MaxtirError/FlexiCubes): In this project, we used a modified version of [Flexicubes](https://github.com/nv-tlabs/FlexiCubes) to support vertex attributes. This modified version is licensed under the [LICENSE](https://github.com/nv-tlabs/FlexiCubes/blob/main/LICENSE.txt).




<!-- Citation -->
## 📜 Citation

If you find this work helpful, please consider citing our paper:

```bibtex
@article{xiang2024structured,
    title   = {Structured 3D Latents for Scalable and Versatile 3D Generation},
    author  = {Xiang, Jianfeng and Lv, Zelong and Xu, Sicheng and Deng, Yu and Wang, Ruicheng and Zhang, Bowen and Chen, Dong and Tong, Xin and Yang, Jiaolong},
    journal = {arXiv preprint arXiv:2412.01506},
    year    = {2024}
}
```

