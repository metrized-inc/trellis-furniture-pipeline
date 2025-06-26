import requests, time

files = [
    ('images', open(r"C:\Users\josephd\Pictures\furniture\salema2\views\three-quarters.jpg", 'rb')),
    ('images', open(r"C:\Users\josephd\Pictures\furniture\salema2\views\front.jpg", 'rb')),
    # Add more images as needed
]

files_png = [
    ('images', open(r"C:\Users\josephd\Downloads\20250410_093221-removebg-preview.png", 'rb'))
]
# response = requests.post('https://furniture.metrized.com/trellis', files=files)
# with open('result.obj', 'wb') as f:
#     f.write(response.content)

# response = requests.post('https://furniture.metrized.com/trellis-glb', files=files)
# with open('model.glb', 'wb') as f:
#     f.write(response.content)


def test_multiview():
    glb_path = r"C:\Users\josephd\Documents\3D Objects\TRELLIS\iq_chair_multi.glb"
    url = 'https://furniture.metrized.com/generate_multiviews'

    # Open the GLB file in binary mode
    with open(glb_path, 'rb') as glb_file:
        files = {
            'glb_file': (glb_file.name, glb_file, 'application/octet-stream')
        }
        # num_views must be sent as form data
        data = {
            'num_views': 32
        }
        response = requests.post(url, files=files, data=data)
        response.raise_for_status()
        with open('views.zip', 'wb') as f:
            f.write(response.content)


def test_async():
    resp = requests.post("https://furniture.metrized.com/trellis_async", files=files_png)
    resp.raise_for_status()
    job = resp.json()
    status_url = "https://furniture.metrized.com" + job["status_url"]

    while True:
        r = requests.get(status_url, stream=True)
        if r.headers.get("Content-Type") == "application/json":
            s = r.json()
            if s["status"] == "finished":
                continue
            if s["status"] == "failed":
                raise RuntimeError(s["error"])
            print(f"Polling Job {job['job_id']} status: {s['status']}")
        else:
            with open("result.glb", "wb") as f:
                f.write(r.content)
            break
        time.sleep(2)           # back-off as needed



if __name__ == "__main__":
    # test_async()
    test_multiview()