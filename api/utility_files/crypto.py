"""
Author: Saurav
Date: 2025-03-10
Description: AES encryption/decryption and HMAC signing module for API calls
"""
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from Crypto.Util.Padding import pad, unpad
import hashlib
from hashlib import sha256
from urllib.parse import unquote, quote
import hmac
import base64
import re
import secrets
import binascii

def format_text(text: str) -> str:
    """
    Function to remove all spaces from a string. This is required before encryption requests for securities.
    :param text: The string from which spaces should be removed
    :return: The string with spaces removed
    """
    text = text.replace(" ", "").replace("\n", "")
    text = re.sub(r'/ /g', '', text)
    text = re.sub(r'/\n/g', '', text)
    text = re.sub(r'/\s+/g', '', text)
    return text


def encode_text(text: str) -> str:
    """
    Function to encode a string into base64. Used when encoding data for the securities View API.
    :param text: The string to be encoded
    :return: The encoded string
    """
    return quote(base64.b64encode(text.encode('utf-8')).decode('utf-8'))


def decode_text(text: str) -> str:
    """
    Function to decode a base64 string back into a regular string. Used when decoding data from the securities View API.
    :param text: The string to be decoded
    :return: The decoded string
    """
    text = unquote(text)
    return unquote(base64.b64decode(text.encode('utf-8')).decode('utf-8'))


def pbkdf2(password: str, salt: str, iterations: int, dklen: int) -> bytes:
    """ Function to compute the PBKDF2 hash """
    return hashlib.pbkdf2_hmac('sha1', password.encode(), salt.encode(), iterations, dklen)


def to_hex(byte_data: bytes) -> str:
    """ Function to convert byte data to a hexadecimal string """
    return binascii.hexlify(byte_data).decode()


def from_hex(hex_str: str) -> bytes:
    """ Function to convert a hexadecimal string back to byte data """
    return binascii.unhexlify(hex_str)


def get_cypher(mode="ECB", primary_key: str = "", secondary_key: str = ""):
    """
    Function to create an AES256 cipher module.
    :param mode: AES mode
    :param primary_key: AES secret key
    :param secondary_key: AES IV (for CBC mode)
    :return: Cipher module
    """
    cipher_mode = None
    if mode == "ECB":
        cipher_mode = AES.MODE_ECB
    elif mode == "CBC":
        cipher_mode = AES.MODE_CBC
    if len(secondary_key) > 0:
        return AES.new(primary_key.encode('utf-8'), cipher_mode, secondary_key.encode('utf-8'))
    return AES.new(primary_key.encode('utf-8'), cipher_mode)


def encrypt_data(key: str, plain_body: str, mode: str = "ECB", secondary_key: str = "") -> str:
    """
    Function to encrypt a given string using AES256 with a secret key.
    :param key: AES secret key
    :param plain_body: The string to be encrypted
    :param mode: AES mode
    :param secondary_key: AES IV (for CBC mode)
    :return: Base64 encoded encrypted string
    """
    cipher = get_cypher(mode, key, secondary_key)
    encrypted_body = cipher.encrypt(pad(plain_body.encode('utf-8'), AES.block_size))
    return base64.b64encode(encrypted_body).decode('utf-8')


def decrypt_data(key: str, encrypted_body: str, mode: str = "ECB", secondary_key: str = "") -> str:
    """
    Function to decrypt a given base64 encoded AES256 encrypted string using a secret key.
    :param key: AES secret key
    :param encrypted_body: The string to be decrypted
    :param mode: AES mode
    :param secondary_key: AES IV (for CBC mode)
    :return: Decrypted string
    """
    decoded_body = base64.b64decode(encrypted_body)
    cipher = get_cypher(mode, key, secondary_key)
    decrypted_body = unpad(cipher.decrypt(decoded_body), AES.block_size).decode('utf-8')
    return decrypted_body


def generate_hs_key(req_data: str, access_token: str) -> str:
    """
    Function to generate the hash key required for securities requests.
    :param req_data: Request data with spaces removed
    :param access_token: The token issued by the securities provider
    :return: The hash key
    """
    hash_object = hmac.new(access_token.encode('utf-8'), req_data.encode('utf-8'), sha256)
    hash_key = base64.b64encode(hash_object.hexdigest().encode('utf-8')).decode('utf-8')
    return hash_key


def generate_signature(data: str, secret_key: str):
    """
    Function to compute the signature for server POST requests and secure responses.
    :param data: The JSON data string
    :param secret_key: The secret key
    :return: The computed signature
    """
    return base64.b64encode(hmac.new(secret_key.encode('utf-8'), data.encode('utf-8'), hashlib.sha256).hexdigest().encode("utf-8"))


def verify_signature(data: str, signature: str, secret_key: str):
    """
    Function to verify the signature of a POST request received by the server.
    :param data: The decrypted request data
    :param signature: The signature from the request data
    :param secret_key: The secret key
    :return: Whether the signature is valid
    """
    decoded_signature = base64.b64decode(signature).decode('utf-8')
    calc_signature = hmac.new(secret_key.encode('utf-8'), data.encode('utf-8'), hashlib.sha256).hexdigest()
    return hmac.compare_digest(calc_signature, decoded_signature)

def generate_secret_key():
    return base64.b64encode(secrets.token_bytes(32))


def encrypt_rsa(public_key: str, data: str, salt: str = "DT"):
    cvtd_pub_key = RSA.import_key(f"-----BEGIN PUBLIC KEY-----\n{public_key}\n-----END PUBLIC KEY-----")
    data_hash = base64.b64encode(SHA256.new(data.encode('utf-8')).digest()).decode('utf-8')
    combined_data = f"{salt}|{data_hash}|{data}".encode('utf-8')
    rsa_cipher = PKCS1_OAEP.new(cvtd_pub_key, hashAlgo=SHA256)
    enc_data = base64.b64encode(rsa_cipher.encrypt(combined_data)).decode('utf-8')
    return enc_data
