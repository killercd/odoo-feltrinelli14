from datetime import datetime
from . import constants
import requests
import logging
import pytz
import json


class Task:
    def __init__(self, ms_access_token, default_env, default_profile, admin_user_email, initial_date=None,
                 end_date=None, folder=None):
        self.__logging = logging.getLogger(__name__)

        self.__ms_access_token = ms_access_token
        self.__default_env = default_env
        self.__default_profile = default_profile
        self.__admin_user_email = admin_user_email
        self.__initial_date = initial_date,
        self.__end_date = end_date
        self.__task_folder = folder
        self.__user_tz = default_env.user.tz or pytz.utc
        self.__local_tz = pytz.timezone(self.__user_tz)

        self.__req_version = constants.MS_VERSION
        self.__base_endpoint = constants.MS_BASE_URL
        self.__req_timeout = constants.MS_REQ_TIMEOUT
        self.__tasks_list = constants.MS_TASKS_CRUD
        self.__task_link = constants.MS_TASK_LINK

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

    def read_serv_tasks(self):
        self.reset_response()
        try:
            req_url = self.__base_endpoint + self.__req_version + self.__tasks_list
            sr_resp = requests.get(req_url, headers=self.__req_headers).json()
            if constants.RESPONSE_ERROR_KEY not in sr_resp:
                _task_list_id = None
                for _sr_list in sr_resp[constants.RESPONSE_VALUE_KEY]:
                    if (self.__task_folder is None and _sr_list["displayName"] == constants.MS_TASK_DEFAULT_LIST) or \
                            (self.__task_folder and _sr_list["displayName"] == self.__task_folder):
                        _task_list_id = _sr_list["id"]
                        break

                if _task_list_id is None:
                    _task_list_id = sr_resp[constants.RESPONSE_VALUE_KEY][0]["id"]
                if _task_list_id:
                    req_url = self.__base_endpoint + self.__req_version + self.__tasks_list + '/' + _task_list_id + \
                              self.__task_link
                    if type(self.__initial_date) is tuple:
                        self.__initial_date = self.__initial_date[0]
                    if self.__initial_date or self.__end_date:
                        req_url += '?$filter='
                        ini = False
                        if self.__initial_date:
                            req_url += "createdDateTime%20ge%20" + \
                                       str(self.__initial_date).replace(' ', 'T') + "Z"
                            ini = True
                        if ini:
                            req_url += '%20and%20'
                        if self.__end_date:
                            req_url += "createdDateTime%20le%20" + \
                                       str(self.__end_date).replace(' ', 'T') + "Z"

                    sr_resp = requests.get(req_url, headers=self.__req_headers).json()
                    if constants.RESPONSE_ERROR_KEY not in sr_resp:
                        self.__js_resp["response"] = sr_resp[constants.RESPONSE_VALUE_KEY]
                        self.__js_resp["total"] = len(sr_resp[constants.RESPONSE_VALUE_KEY])
                        self.__js_resp["err_status"] = False
                    else:
                        self.__logging.info("Task Import Req Failed: " +
                                            str(sr_resp[constants.RESPONSE_ERROR_KEY][constants.RESPONSE_MESSAGE_KEY]))
                        self.__js_resp["response"] = constants.MS_TASKS_IMP_SERV_REQ_ERR
                else:
                    self.__js_resp["response"] = constants.MS_TASKS_IMP_SERV_FOLD_NT
            else:
                self.__js_resp["response"] = sr_resp[constants.RESPONSE_ERROR_KEY][constants.RESPONSE_MESSAGE_KEY]
        except Exception as ex:
            self.__logging.exception("Task Serv Exception found: "+str(ex))
            self.__js_resp["response"] = constants.MS_TASKS_IMP_SERV_EXCEPT

    def import_tasks(self):
        try:
            ur_email = self.__default_profile[constants.MS_PROFILE_EMAIL_FD]
            ur_name = self.__default_profile[constants.MS_PROFILE_NAME_FD]
            partner = self.__default_env[constants.CONTACT_TASK_MODEL].search([('email', '=', ur_email)])
            if partner and len(partner) == 0:
                partner = self.__default_env[constants.OFFICE_CONNECTOR_MODEL].create_contact(ur_email, ur_name)
            partner_id = partner[0].id

            if partner_id:
                self.read_serv_tasks()
                if not self.__js_resp["err_status"]:
                    for _task in self.__js_resp["response"]:
                        try:
                            chk_db_task = self.__default_env[constants.MAIL_ACTIVITY_MODEL].search([
                                ('summary', '=', _task["title"])
                            ])
                            if chk_db_task and len(chk_db_task) > 0:
                                continue
                            else:
                                _due_date = _task["dueDateTime"]["dateTime"].split('.')[0] + '.000'
                                _dte = datetime.strptime(_due_date, '%Y-%m-%dT%H:%M:%S.%f')
                                _due_datetime = self.__local_tz.localize(_dte)

                                self.__default_env[constants.MAIL_ACTIVITY_MODEL].create({
                                    'res_id': partner_id,
                                    'res_model_id': self.__default_env[constants.IR_MODEL].search([
                                        ('model', '=', 'res.partner')]).id,
                                    'user_id': self.__default_env[constants.RES_USERS_MODEL].search([
                                        ('login', '=', self.__admin_user_email)]).id,
                                    'summary': _task["title"],
                                    'activity_type_id': self.__default_env[constants.MAIL_ACTIVITY_TYPE_MODEL].search([
                                        ('name', '=', 'To Do')]).id,
                                    'date_deadline': _due_datetime,
                                    'note': _task["body"]["content"]
                                })
                                self.__js_resp["success"] += 1
                        except Exception as ex:
                            self.__logging.exception("Import DLY task failed: "+str(ex))
                            self.__js_resp["failed"] += 1
            else:
                self.__js_resp["response"] = constants.MS_TASKS_IMP_USER_NOT_FND
        except Exception as ex:
            self.__logging.exception("Task Import Exception: " + str(ex))
            self.__js_resp["response"] = constants.MS_TASKS_IMP_EXCEPT
        return self.__js_resp

    def chk_serv_task(self, req_link, tk_data):
        chk_resp = {"err_status": True, "response": None}
        try:
            req_link += "?$filter=title%20eq%20'" + tk_data["summary"] + "'"
            resp = requests.get(req_link, headers=self.__req_headers).json()
            if constants.RESPONSE_ERROR_KEY not in resp:
                if len(resp[constants.RESPONSE_VALUE_KEY]) > 0:
                    chk_resp["err_status"] = False
        except Exception as ex:
            chk_resp["response"] = "Exception Task Serv: " + str(ex)
        return chk_resp

    def export_serv_tasks(self, db_tasks):
        try:
            req_url = self.__base_endpoint + self.__req_version + self.__tasks_list
            sr_resp = requests.get(req_url, headers=self.__req_headers).json()
            if constants.RESPONSE_ERROR_KEY not in sr_resp:
                _task_list_id = None
                for _sr_list in sr_resp[constants.RESPONSE_VALUE_KEY]:
                    if (self.__task_folder is None and _sr_list["displayName"] == constants.MS_TASK_DEFAULT_LIST) or \
                            (self.__task_folder and _sr_list["displayName"] == self.__task_folder):
                        _task_list_id = _sr_list["id"]
                        break

                if _task_list_id is None:
                    _task_list_id = sr_resp[constants.RESPONSE_VALUE_KEY][0]["id"]
                if _task_list_id:
                    req_url = self.__base_endpoint + self.__req_version + self.__tasks_list + '/' + _task_list_id + \
                              self.__task_link
                    self.__req_headers['Content-Type'] = 'application/json'
                    for _task in db_tasks:
                        chk_resp = self.chk_serv_task(req_url, _task)
                        if chk_resp["err_status"]:
                            try:
                                json_params = {
                                    "title": _task.summary,
                                    "linkedResources": [
                                        {
                                            "webUrl": "http://microsoft.com",
                                            "applicationName": "Microsoft",
                                            "displayName": "Microsoft"
                                        }
                                    ],
                                    "dueDateTime": {
                                        'dateTime': str(_task.date_deadline),
                                        'timeZone': 'UTC'
                                    },
                                    "body": {
                                        "content": _task.note,
                                        "contentType": "html"
                                    }
                                }
                                sr_resp = requests.post(req_url, data=json.dumps(json_params),
                                                        headers=self.__req_headers).json()
                                if constants.RESPONSE_ERROR_KEY not in sr_resp:
                                    self.__js_resp["response"] = sr_resp
                                    self.__js_resp["success"] += 1
                                else:
                                    self.__js_resp = constants.MS_TASKS_EXP_REC_ERR
                                    self.__js_resp["failed"] += 1
                            except Exception as ex:
                                self.__logging.info("Internal export task error:" + str(ex))
                                self.__js_resp["response"] = constants.MS_TASKS_EXP_REC_EXCEPT
                                self.__js_resp["failed"] += 1
                else:
                    self.__js_resp["response"] = constants.MS_TASKS_IMP_SERV_FOLD_NT
            else:
                self.__js_resp["response"] = sr_resp[constants.RESPONSE_ERROR_KEY][constants.RESPONSE_MESSAGE_KEY]
        except Exception as ex:
            self.__logging.exception("Exception Export Tasks: " + str(ex))
            self.__js_resp["response"] = constants.MS_TASKS_EXP_SERV_EXCEPT

    def export_tasks(self):
        self.reset_response()
        try:
            _task_data, query_params = [], []
            partner_id = self.__default_env[constants.CONTACT_TASK_MODEL].search([
                ('email', '=', self.__default_profile[constants.MS_PROFILE_EMAIL_FD])
            ])
            if partner_id and len(partner_id) > 0:
                partner_id = partner_id[0].id
            else:
                partner_id = self.__default_env[constants.CONTACT_TASK_MODEL].create({
                    "name": self.__default_profile[constants.MS_PROFILE_NAME_FD],
                    "email": self.__default_profile[constants.MS_PROFILE_EMAIL_FD]
                }).id

            if self.__initial_date or self.__end_date:
                query_params.append('&')
            query_params.append(('res_id', '=', partner_id))
            if self.__initial_date and self.__end_date:
                query_params.append('&')
            if self.__initial_date:
                query_params.append(('create_date', '>=', str(self.__initial_date).replace('T', ' ')))
            if self.__end_date:
                query_params.append(('create_date', '<=', str(self.__end_date).replace('T', ' ')))

            _db_task_data = self.__default_env[constants.MAIL_ACTIVITY_MODEL].search(query_params)
            if _db_task_data and len(_db_task_data) > 0:
                self.export_serv_tasks(_db_task_data)
                self.__js_resp["total"] = len(_db_task_data)
                self.__js_resp["err_status"] = False
            else:
                self.__js_resp["response"] = constants.MS_TASKS_EXP_REC_NOT_FND
        except Exception as ex:
            self.__logging.exception("Task Export Exception: " + str(ex))
            self.__js_resp["response"] = constants.MS_TASKS_EXP_EXCEPT
        return self.__js_resp
