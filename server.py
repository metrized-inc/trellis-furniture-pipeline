import io
import zipfile
import shutil
import os
from PIL import Image
from fastapi import FastAPI, HTTPException, File, Form, UploadFile, BackgroundTasks
from typing import List
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from multi_image_trellis import trellis_multiple_images
from starlette.background import BackgroundTask
from retex_and_bake import retex_and_bake_endpoint
from model_to_views import model_to_views
from uuid import uuid4
import redis

app = FastAPI()

app.mount("/static", StaticFiles(directory="client/static"), name="static")


@app.get("/", response_class=HTMLResponse)
def root():
    return FileResponse("client/index.html")

@app.post("/trellis")
async def create_mesh(images: List[UploadFile] = File(...)):
    """
    Upload an image file and return the processed mesh.
    """
    contents = []
    for image in images:
        content = await image.read()

        try:
            img = Image.open(io.BytesIO(content))
            img.verify()
            img = Image.open(io.BytesIO(content)).convert("RGB")
        except Exception:
            raise HTTPException(status_code=400, detail=f"File '{image.filename}' is not a valid image.")
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


@app.post("/trellis-glb")
async def create_mesh(images: List[UploadFile] = File(...)):
    """
    Upload an image file and return the processed mesh.
    """
    contents = []
    for image in images:
        content = await image.read()

        try:
            img = Image.open(io.BytesIO(content))
            img.verify()
            img = Image.open(io.BytesIO(content)).convert("RGB")
        except Exception:
            raise HTTPException(status_code=400, detail=f"File '{image.filename}' is not a valid image.")
        contents.append(img)


    data = trellis_multiple_images(contents, postprocessing=False)
    buffer = io.BytesIO(data)

    return StreamingResponse(
        buffer,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": "attachment; filename=model.glb"
        }
    )

rdb = redis.Redis()


@app.post("/trellis_async", status_code=202)
async def create_mesh_async(
    background_tasks: BackgroundTasks,
    images: List[UploadFile] = File(...),
    # Optional parameters can be added here
    sparse_structure_sampler_strength: int = 16,
    slat_sampler_strength: int = 3
    ):
    raw_imgs = [await image.read() for image in images]
    job_id = str(uuid4())
    rdb.hset(job_id, "status", "queued")
    background_tasks.add_task(run_mesh_job, job_id, raw_imgs, sparse_structure_sampler_strength, slat_sampler_strength)
    return {"job_id": job_id, "status_url": f"/trellis/{job_id}"}


def run_mesh_job(job_id: str, raw_imgs: List[bytes], ssss, sss):
    pil_imgs = []
    for b in raw_imgs:
        img = Image.open(io.BytesIO(b)).convert("RGB")
        pil_imgs.append(img)
        
    try:
        meshes = trellis_multiple_images(pil_imgs, False, ssss, sss)
        rdb.hset(job_id, "status", "finished")
        rdb.hset(job_id, "result", meshes)
    except Exception as exc:
        rdb.hset(job_id, "status", "failed")
        rdb.hset(job_id, "error", str(exc))


@app.get("/trellis/{job_id}")
async def mesh_status(job_id: str):
    meta = rdb.hgetall(job_id)
    if not meta:
        raise HTTPException(404, "No such job")
    if meta[b"status"] == b"finished":
        data = meta[b"result"]
        buffer = io.BytesIO(data)
        return StreamingResponse(
            buffer,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": "attachment; filename=model.glb"
            }
        )
    # still running or failed
    return JSONResponse(
        {"status": meta[b"status"].decode(),
         "error": meta.get(b"error", b"").decode()}
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


@app.post("/generate_multiviews")
async def generate_views(
    num_views: int = Form(...),
    glb_file: UploadFile = File(...)
    ):
    temp_folder = os.path.join(os.getcwd(), "tmp", "multiview")
    os.makedirs(temp_folder, exist_ok=True)

    glb_content = await glb_file.read()
    glb_path = os.path.join(temp_folder, glb_file.filename)
    with open(glb_path, "wb") as f:
        f.write(glb_content)

    image_paths = model_to_views(model_path=glb_path, output_path=temp_folder, num_views=num_views)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file_path in image_paths:
            arcname = os.path.relpath(file_path, temp_folder)
            zipf.write(file_path, arcname)
    zip_buffer.seek(0)

    def cleanup_temp():
        shutil.rmtree(temp_folder, ignore_errors=True)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=views.zip"},
        background=BackgroundTask(cleanup_temp)
    )