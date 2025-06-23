import requests, time

files = [
    ('images', open(r"C:\Users\josephd\Pictures\furniture\salema2\views\three-quarters.jpg", 'rb')),
    ('images', open(r"C:\Users\josephd\Pictures\furniture\salema2\views\front.jpg", 'rb')),
    # Add more images as needed
]
# response = requests.post('https://furniture.metrized.com/trellis', files=files)
# with open('result.obj', 'wb') as f:
#     f.write(response.content)

# response = requests.post('https://furniture.metrized.com/trellis-glb', files=files)
# with open('model.glb', 'wb') as f:
#     f.write(response.content)

resp = requests.post("https://furniture.metrized.com/trellis_async", files=files)
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