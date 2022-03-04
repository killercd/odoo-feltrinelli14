from . import constants
import requests
import json
import logging


class Contacts:
    def __init__(self, ms_access_token, default_env, initial_date=None, end_date=None):
        self.__logging = logging.getLogger(__name__)

        self.__ms_access_token = ms_access_token
        self.__default_env = default_env
        self.__initial_date = initial_date
        self.__end_date = end_date
        self.__req_version = constants.MS_VERSION
        self.__base_endpoint = constants.MS_BASE_URL
        self.__crud_contacts = constants.MS_CONTACTS_CRUD
        self.__req_timeout = constants.MS_REQ_TIMEOUT

        self.__req_headers = {"Authorization": "Bearer " + self.__ms_access_token}
        self.__js_resp = {
            "err_status": True,
            "response": None,
            "total": 0,
            "success": 0,
            "failed": 0
        }

    def reset_response(self):
        self.__js_resp["err_status"] = True
        self.__js_resp["response"] = None
        self.__js_resp["total"] = 0
        self.__js_resp["success"] = 0
        self.__js_resp["failed"] = 0

    def read_serv_contacts(self):
        try:
            req_url = self.__base_endpoint + self.__req_version + self.__crud_contacts
            if self.__initial_date or self.__end_date:
                req_url += '?$filter='
                ini = False
                if self.__initial_date:
                    ini = True
                    req_url += "createdDateTime%20ge%20" + str(self.__initial_date).replace(' ', 'T') + "Z"
                if ini:
                    req_url += '%20and%20'
                if self.__end_date:
                    req_url += "createdDateTime%20le%20" + str(self.__end_date).replace(' ', 'T') + "Z"

            sr_resp = requests.get(req_url, headers=self.__req_headers).json()
            if constants.RESPONSE_ERROR_KEY not in sr_resp:
                self.__js_resp["total"] = len(sr_resp[constants.RESPONSE_VALUE_KEY])
                self.__js_resp["response"] = sr_resp[constants.RESPONSE_VALUE_KEY]
                self.__js_resp["err_status"] = False
            else:
                self.__js_resp["response"] = sr_resp[constants.RESPONSE_ERROR_KEY][constants.RESPONSE_MESSAGE_KEY]
        except Exception as ex:
            self.__logging.exception("Server Import Contacts Exception: " + str(ex))
            self.__js_resp["response"] = constants.MS_CONTACTS_IMP_SERV_EXCEPT

    def import_contacts(self):
        self.reset_response()
        try:
            self.read_serv_contacts()
            if not self.__js_resp["err_status"]:
                for _contact in self.__js_resp["response"]:
                    try:
                        query = []
                        if len(_contact["emailAddresses"]) > 0:
                            query.append('&')
                            query.append(('email', '=', _contact["emailAddresses"][0]["address"]))
                        query.append(('name', '=', _contact["displayName"]))

                        chk_contact_exist = self.__default_env[constants.CONTACT_TASK_MODEL].search(query)
                        if chk_contact_exist and len(chk_contact_exist) > 0:
                            pass
                        else:
                            self.__default_env[constants.CONTACT_TASK_MODEL].create({
                                'name': _contact["displayName"],
                                'email': _contact["emailAddresses"][0]["address"] if len(
                                    _contact["emailAddresses"]) > 0 else "",
                                'phone': _contact["mobilePhone"] if _contact["mobilePhone"] else "",
                                'mobile': _contact["businessPhones"][0] if len(
                                    _contact["businessPhones"]) > 0 else "",
                                'street': _contact["homeAddress"] if _contact["homeAddress"] else "",
                                'commercial_company_name': _contact["companyName"] if _contact["companyName"] else "",
                                'city': _contact["homeAddress"]["city"] if len(
                                    _contact["homeAddress"]) > 0 and _contact["homeAddress"]["city"] else "",
                                'zip': _contact["homeAddress"]["postalCode"] if len(
                                    _contact["homeAddress"]) > 0 and _contact["homeAddress"]["postalCode"] else "",
                                'website': _contact["businessHomePage"] if _contact["businessHomePage"] else ""
                            })
                            self.__js_resp["success"] += 1
                    except Exception as ex:
                        self.__logging.info(">> Import SGL Contact Exception: " + str(ex))
                        self.__js_resp["failed"] += 1
        except Exception as ex:
            self.__logging.exception("Import Contacts Exception: " + str(ex))
            self.__js_resp["response"] = constants.MS_CONTACTS_IMP_EXCEPT
        return self.__js_resp

    def check_serv_contact(self, sr_contact):
        chk_resp = {"err_status": True, "response": None}
        try:
            req_url = self.__base_endpoint + self.__req_version + self.__crud_contacts
            req_url += "?$filter=emailAddresses/any(a:a/address eq '" + sr_contact["email"] + "')"
            req_url = req_url.replace(' ', '%20')

            self.__req_headers['Content-Type'] = 'application/json'
            sr_resp = requests.get(req_url, headers=self.__req_headers).json()
            if constants.RESPONSE_ERROR_KEY not in sr_resp:
                if len(sr_resp[constants.RESPONSE_VALUE_KEY]) > 0:
                    chk_resp["err_status"] = False
            else:
                chk_resp["response"] = sr_resp[constants.RESPONSE_ERROR_KEY][constants.RESPONSE_MESSAGE_KEY]
        except Exception as ex:
            chk_resp["response"] = "Check server failure: " + str(ex)
        return chk_resp

    def write_serv_contacts(self, _data):
        self.reset_response()
        try:
            req_url = self.__base_endpoint + self.__req_version + self.__crud_contacts
            self.__req_headers['Content-Type'] = 'application/json'
            for db_cont in _data:
                chk_serv_status = self.check_serv_contact(db_cont)
                if chk_serv_status["err_status"]:
                    try:
                        _name = db_cont['name'].split(' ')
                        json_params = {
                            "givenName": _name[0] if _name[0] and len(_name[0]) > 0 else "",
                            "surname": _name[1] if len(_name) > 1 else "",
                            "emailAddresses": [
                                {
                                    "address": db_cont["email"] if db_cont["email"] else "",
                                    "name": db_cont["name"]
                                }
                            ],
                            "businessPhones": [
                                db_cont["phone"] if "phone" in db_cont and db_cont["phone"] else ""
                            ],
                            "homeAddress": {
                                "street": db_cont["address"] if "address" in db_cont and db_cont["address"] else "",
                                "city": db_cont["city"] if db_cont["city"] else "",
                                "postalCode": db_cont["zip"] if db_cont["zip"] else ""
                            },
                            "mobilePhone": db_cont["mobile"] if "mobile" in db_cont and db_cont["mobile"] else "",
                            "companyName": db_cont["company"] if db_cont["company"] else "",
                            "businessHomePage": db_cont["website"] if db_cont["website"] else ""
                        }
                        sr_resp = requests.post(req_url, data=json.dumps(json_params),
                                                headers=self.__req_headers).json()
                        if constants.RESPONSE_ERROR_KEY not in sr_resp:
                            self.__js_resp["success"] += 1
                        else:
                            self.__logging.info("Internal Error Export Contact: " +
                                                sr_resp[constants.RESPONSE_ERROR_KEY][constants.RESPONSE_MESSAGE_KEY])
                            self.__js_resp["failed"] += 1
                    except Exception as ex:
                        self.__js_resp["failed"] += 1
                        self.__logging.exception("Exception Server Export Contact Internal: " + str(ex))
                        self.__js_resp["response"] = constants.MS_CONTACTS_EXP_EXCEPT
        except Exception as ex:
            self.__logging.exception("Exception Server Export Contact: " + str(ex))
            self.__js_resp["response"] = constants.MS_CONTACTS_EXP_SERV_EXCEPT

    def export_contacts(self):
        self.reset_response()
        try:
            query_params = []
            if self.__initial_date and self.__end_date:
                query_params.append('&')
            if self.__initial_date:
                query_params.append(('write_date', '>=', self.__initial_date))
            if self.__end_date:
                query_params.append(('write_date', '<=', self.__end_date))

            _db_contacts = self.__default_env[constants.CONTACT_TASK_MODEL].search(query_params)
            json_contacts = []
            if _db_contacts and len(_db_contacts) > 0:
                for _db_cont in _db_contacts:
                    json_contacts.append({
                        "name": _db_cont.name,
                        "company": _db_cont.commercial_company_name,
                        "email": _db_cont.email,
                        "phone": _db_cont.phone,
                        "mobile": _db_cont.mobile,
                        "street": _db_cont.street,
                        "city": _db_cont.city,
                        "zip": _db_cont.zip,
                        "website": _db_cont.website
                    })
                if len(json_contacts) > 0:
                    self.write_serv_contacts(_data=json_contacts)
                    self.__js_resp["err_status"] = False
                else:
                    self.__js_resp["response"] = constants.MS_CONTACTS_EXP_NOT_FND
            else:
                self.__js_resp["response"] = constants.MS_CONTACTS_EXP_NOT_FND
        except Exception as ex:
            self.__logging.exception("Export Contacts Exception: " + str(ex))
            self.__js_resp["response"] = constants.MS_CONTACTS_EXP_EXCEPT
        return self.__js_resp
