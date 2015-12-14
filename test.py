import requests
import base64
import json


def run_post():

    with open("./data/cat.jpg", "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
    url = 'http://localhost:5000/android_post'
    data = {'filename': 'cat.jpg', 'image':encoded_string, 'longitude': 38.436236, 'latitude': 88.36236236}
    headers = {'Content-Type': 'application/json'}

    r = requests.post(url, data=json.dumps(data), headers=headers)
run_post()  
