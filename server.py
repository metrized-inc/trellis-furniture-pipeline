from fastapi import FastAPI, HTTPException, File, UploadFile
from typing import List
from fastapi.responses import StreamingResponse
from multi_image_trellis import trellis_multiple_images
import io
from PIL import Image
import json
from utils import make_temp_material

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


@app.post("retex")
async def retexture_mesh(file: UploadFile = File(...)):
    content = await file.read()
    try:
        data = json.load(io.BytesIO(content))
        for i, group in enumerate(data):
            group_materials = []
            for material in group:
                make_temp_material(material, i)
        
        with open("tmp/materials.json", "w") as outfile:
            json.dump(data, outfile)

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format.")