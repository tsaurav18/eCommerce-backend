import base64
import hashlib
import hmac
import random
import pandas as pd
import json
import uuid
from api.models import User

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
