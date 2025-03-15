"""
Author:Saurav
Date: 2025-10-03
Description: Module that abstracts API requests and responses
"""
import requests
from rest_framework import status
from rest_framework.response import Response
from api.utility_files import crypto
from django.http import JsonResponse
from django.conf import settings
from typing import Optional

import logging
import json

logger = logging.getLogger('apicall')

API_STATUS_OK = 200
API_STATUS_BAD_REQUEST = 400
API_STATUS_SERVICE_UNAVAILABLE = 503
API_STATUS_FAILED = 9999

SECRET_KEY = settings.ECOM_SECRET

def default_result_handler(result: dict) -> 'APIResponse':
    return APIResponse(API_STATUS_OK, "Success", data=result)


class APIRequest:
    def __init__(
            self,
            url="",
            test_url="",
            endpoint="",
            method="POST",
            headers=None,
            body=None,
            data_header=None,
            data_body=None,
            result_handler=default_result_handler):
        """
        :param url:         API request URL
        :param test_url:    API test URL
        :param endpoint:    API endpoint
        :param method:      API method (e.g., POST, GET)
        :param headers:     Request HTTP headers
        :param data_header: Request data header
        :param data_body:   Request data body
        """
        if data_body is None:
            data_body = {}
        if data_header is None:
            data_header = {}
        if headers is None:
            headers = {}
        self.url = url
        self.test_url = test_url
        self.endpoint = endpoint
        self.method = method
        self.headers = headers
        self.data_header = data_header
        self.data_body = data_body
        self.body = body
        self.handle_result = result_handler

    def get_url(self) -> str:
        return self.url

    def get_test_url(self) -> str:
        return self.test_url

    def get_method(self) -> str:
        return self.method

    def get_endpoint(self) -> str:
        return self.endpoint

    def get_headers(self) -> dict:
        return self.headers

    def get_data_header(self) -> dict:
        return self.data_header

    def get_data_body(self) -> Optional[dict]:
        return self.data_body

    def update_headers(self, headers: dict) -> None:
        self.headers = {
            **self.headers,
            **headers
        }

    def update_data_header(self, data_header: dict, replace: bool = True) -> None:
        if replace:
            self.data_header = {
                **self.data_header,
                **data_header
            }
        else:
            self.data_header = {
                **data_header,
                **self.data_header
            }

    def update_data_body(self, data_body: dict) -> None:
        self.data_body = {
            **self.data_body,
            **data_body
        }

    def get_request_data(self) -> dict:
        data_header = {
            **self.data_header,
            'bizUnit': self.endpoint.split('/')[-1]
        }
        if self.body is not None:
            return self.body
        return {
            "dataHeader": data_header,
            "dataBody": self.data_body
        }

    def get_result_data(self, result):
        return result.json()

    def call(self, test=False):
        url = self.url
        if test:
            url = self.test_url
            logger.info(f"API is running in test mode: {url}{self.endpoint}")
        request_data = self.get_request_data()
        result = requests.post(f"{url}{self.endpoint}", headers=self.headers, json=request_data)
        result_data = self.get_result_data(result)
        response = self.handle_result(result_data)

        return response


class APIResponse:
    def __init__(self, api_status=400, api_msg="Invalid access", headers=None, data=None, http_headers=None):
        """
        :param api_status:  API result code
        :param api_msg:     API result message
        :param headers:     Response data headers
        :param data:        Response data body
        """
        if data is None:
            data = {}
        if headers is None:
            headers = {}
        self.api_status = api_status
        self.api_msg = api_msg
        self.headers = headers
        self.data = data
        self.http_headers = http_headers

    def get_api_status(self):
        return self.api_status

    def get_api_message(self):
        return self.api_msg

    def get_headers(self):
        return self.headers

    def format_response_data(self):
        return {
            "header": {
                "api_status": self.api_status,
                "api_msg": self.api_msg,
                **self.headers
            },
            "body": self.data
        }

    def get_response_data(self):
        return self.format_response_data()

    def secure(self):
        return SecureAPIResponse(
            api_status=self.api_status,
            api_msg=self.api_msg,
            headers=self.headers,
            data=self.data,
            http_headers=self.http_headers,
            secret_key=SECRET_KEY
        )

    def rest(self, http_status=status.HTTP_200_OK):
        return Response(self.get_response_data(), headers=self.http_headers, status=http_status)

    def http(self, http_status=status.HTTP_200_OK):
        response = JsonResponse(self.get_response_data(), status=http_status)

        if self.http_headers is None:
            return response
        for k, v in self.http_headers.items():
            response[k] = v
        return response

    # deprecated
    def send(self, http_status=status.HTTP_200_OK, response_type="REST"):
        if response_type == "REST":
            return self.rest(http_status=http_status)
        return self.http(http_status=http_status)


class SecureAPIRequest(APIRequest):
    def __init__(self, client_secret="", access_token="", *args, **kwargs):
        """
        :param client_secret:   App secret
        :param access_token:    Access token
        :param args:
        :param kwargs:
        """
        super().__init__(*args, **kwargs)
        self.client_secret = client_secret
        self.access_token = access_token

    # @Override
    def get_request_data(self):
        data_header = {
            **self.data_header,
            'bizUnit': self.endpoint.split('/')[-1]
        }

        request_data = {
            "dataHeader": data_header,
            "dataBody": self.data_body
        }
        request_data = json.dumps(request_data, ensure_ascii=False)
        request_data = crypto.format_text(request_data)
        encrypted_data = crypto.encrypt_data(self.client_secret, request_data)
        hs_key = crypto.generate_hs_key(request_data, self.access_token)
        self.update_headers({
            "hsKey": hs_key
        })
        return {
            "encrypt": encrypted_data
        }

    # @Override
    def get_result_data(self, result):
        result_json = result.json()
        encrypt_data = result_json.get("encrypt", "")
        decrypted_data = crypto.decrypt_data(self.client_secret, encrypt_data)
        decrypted_json = json.loads(decrypted_data)
        return decrypted_json


class SecureAPIResponse(APIResponse):
    def __init__(self, secret_key, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.secret_key = secret_key
        if self.http_headers is None:
            self.http_headers = {}

    # @Override
    def get_response_data(self):
        response_data = self.format_response_data()
        plain_data = json.dumps(response_data, ensure_ascii=False)  # crypto.format_text(json.dumps(response_data, ensure_ascii=False))
        encrypted_data = crypto.encrypt_data(self.secret_key, plain_data)
        signature = crypto.generate_signature(plain_data, self.secret_key)
        self.http_headers["X-Signature"] = signature
        return {
            "enc_data": encrypted_data,
            "signature": signature
        }

