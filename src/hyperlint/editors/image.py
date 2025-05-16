import base64

from loguru import logger
from openai import OpenAI

from ..config import SimpleConfig

client = OpenAI()


def generate_image(prompt: str, config: SimpleConfig):
    result = client.images.generate(model="gpt-image-1", prompt=prompt)

    if result.data:
        image_base64 = result.data[0].b64_json
        if image_base64:
            image_bytes = base64.b64decode(image_base64)

            # Save the image to a file
            with open("otter.png", "wb") as f:
                f.write(image_bytes)
            return

    logger.warning("Failed to generate image")
