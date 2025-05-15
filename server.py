import io
import zipfile
import shutil
import os
from PIL import Image
from fastapi import FastAPI, HTTPException, File, UploadFile
from typing import List
from fastapi.responses import StreamingResponse
from multi_image_trellis import trellis_multiple_images
from starlette.background import BackgroundTask
from retex_and_bake import retex_and_bake_endpoint

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Hello World"}

@app.post("/trellis")
async def create_mesh(files: List[UploadFile] = File(...)):
    """
    Upload an image file and return the processed mesh.
    """
    contents = []
    for file in files:
        content = await file.read()

        try:
            img = Image.open(io.BytesIO(content))
            img.verify()
            img = Image.open(io.BytesIO(content)).convert("RGB")
        except Exception:
            raise HTTPException(status_code=400, detail=f"File '{file.filename}' is not a valid image.")
        contents.append(img)


    data = trellis_multiple_images(contents)
    buffer = io.BytesIO(data)

    return StreamingResponse(
        buffer,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": "attachment; filename=processed.obj"
        }
    )


@app.post("/retexure")
async def retexture_mesh(
    images: List[UploadFile] = File(...),
    glb_file: UploadFile = File(...)
    ):

    temp_folder = "tmp/retex"
    os.makedirs(temp_folder, exist_ok=True)
    json_path = None

    # Save each image
    for image in images:
        content = await image.read()
        image_path = os.path.join(temp_folder, image.filename)
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        # SAVE PATH OF JSON FILE
        if image.filename.endswith(".json"):
            json_path = image_path

        with open(image_path, "wb") as f:
            f.write(content)
    
    # Save the GLB file
    glb_content = await glb_file.read()
    glb_path = os.path.join(temp_folder, glb_file.filename)
    with open(glb_path, "wb") as f:
        f.write(glb_content)

    if json_path is None:
        raise HTTPException(status_code=400, detail="No JSON could be found, please check your materials folder")
    
    HDRI_PATH = "hdris\studio_small_09_1k.exr"
    HDRI_STRENGTH = 1.0
    TEXTURE_SIZE = 4096
    DENOISE = False
    SAMPLES = 40

    retex_and_bake_endpoint(
        glb_path,
        json_path,
        HDRI_PATH,
        HDRI_STRENGTH,
        TEXTURE_SIZE,
        DENOISE,
        SAMPLES
    )

    # Zip the "baked_textures" folder
    baked_folder = os.path.join(temp_folder, "baked_textures")
    if not os.path.isdir(baked_folder):
        raise HTTPException(status_code=500, detail=f"Expected folder '{baked_folder}' not found.")
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        # Walk the baked_textures folder and add all files.
        for root, dirs, files in os.walk(baked_folder):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, baked_folder)
                zipf.write(file_path, arcname)
    zip_buffer.seek(0)
    
    # Define cleanup function to remove the temporary folder after response.
    def cleanup_temp():
        shutil.rmtree(temp_folder, ignore_errors=True)
    
    # Return a StreamingResponse with the zip file and schedule cleanup.
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=baked_textures.zip"},
        background=BackgroundTask(cleanup_temp)
    )