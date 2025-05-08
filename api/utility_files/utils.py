import base64
import hashlib
import hmac
import random
import pandas as pd
import json
import uuid
from api.models import User
import os

from ecombackend import settings


def hex_to_62(number):
    # 긴 sha256 16진수 결과값을 62진수로
    BASE = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    if number == 0:
        return BASE[0]
    result = []
    while number:
        number, rem = divmod(number, 62)
        result.append(BASE[rem])
    return ''.join(reversed(result))

def generate_user_id(name : str, email : str, max_iter : int = 1):
    HASH_SPLIT_LIMIT = 16 # 5000만명 정도에도 충돌 가능성이 낮음

    for _ in range(max_iter):
        unique_string = f"{uuid.uuid4()}|{name}|{email}"
        hashed = hashlib.sha256(unique_string.encode()).hexdigest()[:HASH_SPLIT_LIMIT]
        hash_number = int(hashed, 16)
        user_id = hex_to_62(hash_number)
        if not User.objects.filter(user_id=user_id).exists():
            return user_id
        else:
            print("user_id collision detected, regenerating...")
    print(f"user_id collision still detected after {max_iter} attempts. Terminating...")
    return None


def save_video(base64_string, *, video_directory='default', remove_header=True, ext='mp4'):
    # Remove header (e.g., "data:video/mp4;base64,") if needed
    if remove_header:
        base64_string = base64_string.split(",")[-1]

    # Decode the base64 string into bytes
    video_data = base64.b64decode(base64_string)
    # Generate a unique filename based on the video content
    video_hash = hashlib.sha256(video_data).hexdigest()
    stories_dir = os.path.join('media', video_directory)

    # Ensure the directory exists
    os.makedirs(stories_dir, exist_ok=True)

    # Build the full file path using the given extension (default is mp4)
    filename = f'{video_hash}.{ext}'
    video_path = os.path.join(stories_dir, filename)

    # Save the video file
    with open(video_path, "wb") as video_file:
        video_file.write(video_data)

    return video_path


def save_image(base64_string, *, image_directory='default', remove_header=True, ext='png'):
    # If remove_header is True, try to extract the image format from the header.
    if remove_header:
        if base64_string.startswith("data:"):
            # Expected format: "data:image/png;base64,xxxxx"
            header, base64_data = base64_string.split(",", 1)
            # Extract MIME type, e.g. "image/png" and then get "png"
            try:
                ext_from_header = header.split(";")[0].split("/")[1]
                ext = ext_from_header  # Override passed ext
            except IndexError:
                pass  # fallback to provided ext if parsing fails
            base64_string = base64_data
        else:
            # If there is no proper header, remove any accidental prefixes.
            base64_string = base64_string.split(",")[-1]

    # Decode the base64 string into bytes
    image_data = base64.b64decode(base64_string)

    # Generate a unique filename based on the image content
    image_hash = hashlib.sha256(image_data).hexdigest()

    # Ensure the directory exists
    images_dir = os.path.join('media', image_directory)
    os.makedirs(images_dir, exist_ok=True)

    # Build the full file path using the determined extension
    filename = f'{image_hash}.{ext}'
    image_path = os.path.join(images_dir, filename)

    # Save the image file
    with open(image_path, "wb") as image_file:
        image_file.write(image_data)

    return image_path