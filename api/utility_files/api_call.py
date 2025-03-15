"""
Author: Saurav
Date: 2025-03-10
Description: API Helper
"""
from ecombackend.settings import ECOM_ENV
from api.utility_files.apibase import APIRequest, APIResponse, API_STATUS_OK, API_STATUS_FAILED
from typing import Optional
import requests
import traceback
import logging

logger = logging.getLogger('apicall')


def api_success(api_msg: str = "Success", headers: Optional[dict] = None, body: Optional[dict] = None) -> 'APIResponse':
    """
    Returns a success response for the API.
    :param api_msg: Response message
    :param headers: Additional data to include in the API headers apart from the default headers
    :param body: Data to include in the body of the API response
    :return: APIResponse
    """
    return APIResponse(API_STATUS_OK, api_msg, headers, body)


def api_failed(api_msg: str = "Failure", headers: Optional[dict] = None):
    """
    Returns a failure response for the API.
    :param api_msg: Response message
    :param headers: Additional data to include in the API headers apart from the default headers
    :return: APIResponse
    """
    return APIResponse(API_STATUS_FAILED, api_msg, headers)


def call_api(api_request: APIRequest, *, data_header: Optional[dict] = None, http_header: Optional[dict] = None) -> 'APIResponse':
    """
    Calls an API and returns the response.
    :param api_request: APIRequest
    :param data_header: Header to include in the HTTP body
    :param test: Testing environment flag
    :param http_header: HTTP headers
    :return: API response result (APIResponse)
    """
    test = (ECOM_ENV == "development")
    try:
        if data_header is not None:
            api_request.update_data_header(data_header, replace=False)
        if http_header is not None:
            api_request.update_headers(http_header)
        return api_request.call(test)
    except requests.exceptions.HTTPError as http_error:
        return api_failed("HTTP Error", {"http_status": http_error.response.status_code})
    except Exception as e:
        logger.warning(f"[API Error] An error occurred while making the API request (Request URL: "
                       f"{api_request.get_test_url() if test else api_request.get_url()}{api_request.get_endpoint()})")
        logger.warning(traceback.format_exc())
        return api_failed("Server Error.")


def get_body_data(request, key, default="", required=False):
    """
    Function to get data from the request using the key.
    This works like dict.get, but is used for consistency.
    :param request: DRF request object
    :param key: Key for the data
    :param default: Default value if the key is not found
    :param required: If True, raises ValueError if the key is not found
    :return: Value for the given key
    """
    if key in request.data:
        return request.data[key]
    if required:
        raise ValueError(f"The key {key} does not exist in the data.")
    return default
