<h1 align="center">Pictures to retextured 3D Models<br>powered by TRELLIS</h1>
<p align="center"><a href="https://arxiv.org/abs/2412.01506">

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
    cd trellis-furniture-pipeline
    make install

<!-- Usage -->
## HOW TO USE (do these steps in order)
NOTE: Before running any of the scripts, activate the venv with ".venv/scripts/activate"

**1.TRELLIS PIPELINE**
- This pipeline feeds a folder of images to TRELLIS, and then performs some post processing to remove duplicate verticies and auto-unwrap the UV Map
- To run it, use the command "python trellis_and_proccess.py --image_folder='path/to/your/image/folder'"
- The outputs will be placed in a folder called "trellis_out" in the same directory as your image folder.

**2.MANUAL STEP**
- Take the .obj outputted by trellis and load it into Blender or your preferred 3d software
- Assign different materials to different parts of your object (e.g. you can select the legs of a chair out and assign it to another material)
- Export the object as a .glb
- NOTE: The final step can take in as many different material groups as you want, if you do not make a material it will automatically assign one to the whole model

**3.RETEXTURE PIPELINE**
- This step requires you to setup a .json file that specifies the materials you want to apply
- It should be formatted in the way shown in material-example.json
- Each material should have a name (for naming baked outputs), and can hold the following properties (each should be an image path), only the first one is needed for it to be a valid material: ["diffuse", "roughness", "metallic", "normal", "ambient_occlusion", "orm"]. In addition, you can specify the scale with the "scale" property
- To run the pipeline: "python retex_and_bake.py --material_json='path/to/json' --model_path='path/to/your/model'"
- Here is a full list of the flags you can use (only the first two are required):
    - --material_json TEXT    Path to the json file that specifies the materials, look at material-example.json for reference.
    - --model_path TEXT       Path to the .glb file you exported in step 2.
    - --hdri_path TEXT        Path to the HDRI image (.exr).
    - --hdri_strength FLOAT   Strength of the HDRI lighting. Default is 1.0.
    - --texture_size INTEGER  Size of the texture to bake. Default is 4096.
    - --denoise BOOLEAN       Whether to use denoising. Default is False. (Seams
                          will appear if set to True)
    - --samples INTEGER       Number of samples for baking. Default is 40.
    - --export_glb BOOLEAN    Whether to export a baked GLB model instead of a texture map. Default is False.
    - --help                  Show this message and exit.
- The outputs will be a folder of .png textures, this folder will be located in the same directory as the model you specified
- These textures can easily be applied to the .obj that was outputted in step 1. For best results apply it as an emission texture so it is not affected by the lighting in the scene


<!-- License -->
## ⚖️ License

TRELLIS models and the majority of the code are licensed under the [MIT License](LICENSE). The following submodules may have different licenses:
- [**diffoctreerast**](https://github.com/JeffreyXiang/diffoctreerast): We developed a CUDA-based real-time differentiable octree renderer for rendering radiance fields as part of this project. This renderer is derived from the [diff-gaussian-rasterization](https://github.com/graphdeco-inria/diff-gaussian-rasterization) project and is available under the [LICENSE](https://github.com/JeffreyXiang/diffoctreerast/blob/master/LICENSE).


- [**Modified Flexicubes**](https://github.com/MaxtirError/FlexiCubes): In this project, we used a modified version of [Flexicubes](https://github.com/nv-tlabs/FlexiCubes) to support vertex attributes. This modified version is licensed under the [LICENSE](https://github.com/nv-tlabs/FlexiCubes/blob/main/LICENSE.txt).


