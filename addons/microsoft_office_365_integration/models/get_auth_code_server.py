from urllib.parse import urlencode
from . import constants
import requests


def get_authorization_url(credentials):
    qry_params = {
        'client_id': credentials['client_id'],
        'redirect_uri': credentials['redirect_url'],
        'response_type': 'code',
        'scope': " ".join(constants.MS_SCOPES),
        'response_mode': 'query',
        'state': '12345'

    }
    return constants.MS_AUTH_URL + "?" + urlencode(qry_params)


def get_authorize_token(code, credentials):
    params = {
        "client_id": credentials['client_id'],
        "client_secret": credentials['client_secret'],
        "redirect_uri": credentials['redirect_url'],
        "code": code,
        "response_type": "code",
        "grant_type": "authorization_code"
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(constants.MS_AUTH_EXCODE_URL, data=params, headers=headers).json()
    return response


def get_refresh_authorize_token(refresh_token, credentials):
    params = {
        "client_id": credentials['client_id'],
        "client_secret": credentials['client_secret'],
        "redirect_uri": credentials['redirect_url'],
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(constants.MS_AUTH_EXCODE_URL, data=params, headers=headers).json()
    return response
