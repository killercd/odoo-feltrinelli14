from . import constants
import requests
import logging


class Profile:
    def __init__(self, ms_access_token):
        self.__logging = logging.getLogger(__name__)

        self.__ms_access_token = ms_access_token
        self.__req_version = constants.MS_VERSION
        self.__base_endpoint = constants.MS_BASE_URL
        self.__req_timeout = constants.MS_REQ_TIMEOUT
        self.__profile_me = constants.MS_PROFILE_LINK

        self.__req_headers = {"Authorization": "Bearer " + self.__ms_access_token}
        self.__js_resp = {
            "err_status": True,
            "response": "",
            "addons": None
        }

    def reset_response(self):
        self.__js_resp["err_status"] = True
        self.__js_resp["response"] = ""
        self.__js_resp["addons"] = None

    def get_profile(self):
        self.reset_response()
        try:
            req_url = self.__base_endpoint + self.__req_version + self.__profile_me
            resp = requests.get(req_url, headers=self.__req_headers).json()
            self.__logging.info(resp)
            if constants.RESPONSE_ERROR_KEY not in resp:
                self.__js_resp["response"] = resp
                self.__js_resp["err_status"] = False
            else:
                self.__js_resp["response"] = resp[constants.RESPONSE_ERROR_KEY]
        except Exception as ex:
            self.__logging.exception("Office 365 Profile Exception: " + str(ex))
            self.__js_resp["response"] = constants.MS_PROFILE_EXCEPT
        return self.__js_resp
