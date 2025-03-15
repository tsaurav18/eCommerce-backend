"""
Author: Saurav
Date: 2025-3-10
Description: This module includes middleware that validates and decrypts POST requests made to ECOM.
"""

from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from api.utility_files.api_call import api_failed
from api.utility_files.crypto import decrypt_data, verify_signature
import json
import traceback

SECRET_KEY = settings.ECOM_SECRET
print('SECRET_KEY in middleware',SECRET_KEY)
SIGNATURE_HEADER_NAME = 'X-Signature'

ERROR_MISSING_X_SIGNATURE = 'Invalid signature.'
ERROR_INVALID_REQUEST_BODY_FORMAT = 'Request body format is incorrect.'
ERROR_INVALID_SIGNATURE = 'Invalid signature.'
ERROR_SERVER_VERIFICATION_FAILED = 'Error occurred while processing encrypted data.'


class SecureRequestMiddleware(MiddlewareMixin):

    def _accept(self, request):
        request.ecom_secure_request_processing_done = True
        return None

    def _reject(self, reason):
        return api_failed(reason).http()

    def process_view(self, request, view_func, view_args, view_kwargs):
        try:
            path_list = request.path_info.strip('/').split('/')
            baseurl = path_list[0]

            if baseurl not in ['api', 'ecom']:  # Adjust based on actual API base path
                return None

            if request.method != 'POST':
                return None

            if len(path_list) > 1 and path_list[1] == 'web':
                return None

            if request.content_type != 'application/json':
                return self._reject(ERROR_INVALID_REQUEST_BODY_FORMAT)

            signature = request.headers.get('X-Signature')

            if not signature:
                return self._reject(ERROR_MISSING_X_SIGNATURE)

            try:
                request_data = json.loads(request.body)
                encrypted_data = request_data.get('enc_data', '')
            except (ValueError, KeyError):
                return self._reject(ERROR_INVALID_REQUEST_BODY_FORMAT)

            if encrypted_data == '':
                return self._reject(ERROR_INVALID_REQUEST_BODY_FORMAT)

            decrypted_data = decrypt_data(SECRET_KEY, encrypted_data)

            if not verify_signature(decrypted_data, signature, SECRET_KEY):
                return self._reject(ERROR_INVALID_SIGNATURE)

            try:
                decrypted_body = json.loads(decrypted_data)
                request._body = json.dumps(decrypted_body).encode('utf-8')
                request.POST = request.POST.copy()
                request.data = json.loads(decrypted_data)

            except (ValueError, KeyError):
                return self._reject(ERROR_INVALID_REQUEST_BODY_FORMAT)

        except Exception as e:
            traceback.print_exc()
            return self._reject(ERROR_SERVER_VERIFICATION_FAILED)

        return self._accept(request)
