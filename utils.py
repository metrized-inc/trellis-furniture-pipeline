import bpy, bmesh


def import_glb_merge_vertices(model_path, *, merge_threshold=1e-4):
    # Clear the current scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # 1. Import the GLB ---------------------------------------------------------
    bpy.ops.import_scene.gltf(filepath=str(model_path), merge_vertices=True)
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not meshes:
        raise ValueError("The GLB contains no mesh objects")

    # 2. Join them (still needs an operator, so keep the override) -------------
    with bpy.context.temp_override(active_object=meshes[0],
                                   selected_objects=meshes,
                                   mode="OBJECT"):
        if len(meshes) > 1:
            bpy.ops.object.join()

    merged_obj = meshes[0]          # join collapses into the first mesh

    # 3. Remove doubles without touching Edit-Mode -----------------------------
    bm = bmesh.new()
    bm.from_mesh(merged_obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=merge_threshold)  # :contentReference[oaicite:0]{index=0}
    bm.to_mesh(merged_obj.data)
    bm.free()

    merged_obj.data.update()        # flush BMesh changes to GPU / depsgraph
    return merged_obj


def add_file_to_temp(file_path, subfolder=""):
    """
    Adds a file to the temporary directory, returns the temporary file path.
    """
    import shutil
    import os

    temp_dir = "tmp"
    temp_file_path = os.path.join(temp_dir, subfolder, os.path.basename(file_path))
    
    shutil.copy(file_path, temp_file_path)
    
    return temp_file_path


def make_temp_material(material, group_num):
    image_keys = [  "diffuse",
                    "roughness",
                    "metallic",
                    "normal",
                    "ambient_occlusion",
                    "orm"]
    for key in image_keys:
        tmp_path = add_file_to_temp(material.get(key), subfolder=str(group_num))
        material[key] = tmp_path