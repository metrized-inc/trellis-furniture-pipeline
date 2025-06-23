import requests

files = [
    ('images', open(r"C:\Users\josephd\Pictures\furniture\salema2\views\three-quarters.jpg", 'rb')),
    ('images', open(r"C:\Users\josephd\Pictures\furniture\salema2\views\front.jpg", 'rb')),
    # Add more images as needed
]
# response = requests.post('https://furniture.metrized.com/trellis', files=files)
# with open('result.obj', 'wb') as f:
#     f.write(response.content)

response = requests.post('https://furniture.metrized.com/trellis-glb', files=files)
with open('model.glb', 'wb') as f:
    f.write(response.content)