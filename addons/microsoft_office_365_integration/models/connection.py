from . import get_auth_code_server
from . import constants
from . import profile
import logging


class Connection:
    def __init__(self, azure_app_cred=None, default_env=None):
        self.__logging = logging.getLogger(__name__)

        self.__azure_app_credentials = azure_app_cred
        self.__default_env = default_env
        self.__default_graph_url = constants.MS_BASE_URL
        self.__scopes = constants.MS_SCOPES
        self.__grant_code = None
        self.__access_token = None
        self.__refresh_token = None

        self.__js_resp = {
            "err_status": True,
            "response": '',
            "addons": None
        }

    def reset_response(self):
        self.__js_resp["err_status"] = True
        self.__js_resp["response"] = ""
        self.__js_resp["addons"] = None

    def get_access_token(self):
        return self.__access_token

    def get_refresh_token(self):
        return self.__refresh_token

    def get_auth_url(self):
        self.reset_response()
        try:
            if self.__azure_app_credentials:
                auth_url = get_auth_code_server.get_authorization_url(self.__azure_app_credentials)
                if auth_url != '':
                    self.__js_resp["response"] = auth_url
                    self.__js_resp["err_status"] = False
                else:
                    self.__js_resp["response"] = constants.MS_CONN_URL_FAILED
            else:
                self.__js_resp["response"] = constants.MS_CONN_URL_FAILED
        except Exception as ex:
            self.__logging.exception("Connection GEN URL Except: " + str(ex))
            self.__js_resp["response"] = constants.MS_CONN_URL_EXCEPT
        return self.__js_resp

    def generate_access_token(self, grant_code):
        self.reset_response()
        try:
            response = get_auth_code_server.get_authorize_token(grant_code, self.__azure_app_credentials)
            if constants.RESPONSE_ERROR_KEY not in response:
                if 'access_token' in response:
                    self.__access_token = response["access_token"]
                if 'refresh_token' in response:
                    self.__refresh_token = response["refresh_token"]
                self.__js_resp["err_status"] = False
            else:
                self.__js_resp["response"] = constants.MS_CONN_CRED_FAILED
        except Exception as ex:
            self.__logging.exception("Connection Credential Failed: " + str(ex))
            self.__js_resp["response"] = constants.MS_CONN_CRED_EXCEPT
        return self.__js_resp

    def refresh_access_token(self, refresh_token):
        self.reset_response()
        try:
            resp = get_auth_code_server.get_refresh_authorize_token(refresh_token, self.__azure_app_credentials)
            if constants.RESPONSE_ERROR_KEY not in resp:
                if 'access_token' in resp:
                    self.__access_token = resp['access_token']
                if 'refresh_token' in resp:
                    self.__refresh_token = resp["refresh_token"]
                self.__js_resp["err_status"] = False
            else:
                self.__js_resp["response"] = constants.MS_CONN_RAT_FAILED
        except Exception as ex:
            self.__logging.exception("Connection RAT Exception: " + str(ex))
            self.__js_resp["response"] = constants.MS_CONN_RAT_EXCEPT
        return self.__js_resp

    def get_msv_access_token(self):
        self.reset_response()
        try:
            db_cursor = self.__default_env[constants.OFFICE_CREDENTIALS_MODEL]
            db_rows = db_cursor.search([])

            if db_rows and len(db_rows) > 0:
                _db_row = db_rows[constants.DEFAULT_INDEX]
                _resp_acc_token = _db_row.access_token

                if _resp_acc_token and _resp_acc_token != "":
                    max_attempt = constants.ACCESS_TOKEN_ATTEMPT
                    while max_attempt > 0:
                        _profile = profile.Profile(ms_access_token=_resp_acc_token)
                        p_response = _profile.get_profile()
                        if not p_response["err_status"]:
                            self.__js_resp["response"] = _resp_acc_token
                            self.__js_resp["err_status"] = False
                            self.__js_resp["addons"] = p_response["response"]
                            break
                        elif constants.TOKEN_ERR_STATUS_CODE == p_response["response"]["code"]:
                            rat_response = self.refresh_access_token(refresh_token=_db_row.refresh_token)
                            if not rat_response["err_status"]:
                                _resp_acc_token = self.get_access_token()
                                _db_row.access_token = self.get_access_token()
                                _db_row.refresh_token = self.get_refresh_token()
                                db_cursor.update(_db_row)
                            else:
                                self.__js_resp["response"] = constants.ACCESS_TOKEN_ERR_REFRESH
                        else:
                            self.__js_resp["response"] = constants.ACCESS_TOKEN_INVALID
                        max_attempt -= 1
                else:
                    self.__js_resp["response"] = constants.ACCESS_TOKEN_NOT_FND
            else:
                self.__js_resp["response"] = constants.ACCESS_TOKEN_CRED_NOT_FND
        except Exception as ex:
            self.__logging.exception("Unable to get auth credentials: " + str(ex))
            self.__js_resp["response"] = str(ex)
        return self.__js_resp
