import base64

from openai import OpenAI

client = OpenAI()


def generate_image(prompt: str):
    result = client.images.generate(model="gpt-image-1", prompt=prompt)

    image_base64 = result.data[0].b64_json
    image_bytes = base64.b64decode(image_base64)

    # Save the image to a file
    with open("otter.png", "wb") as f:
        f.write(image_bytes)
