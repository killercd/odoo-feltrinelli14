from . import constants
import requests
import logging
import base64


class OneDrive:
    def __init__(self, ms_access_token, initial_date=None, end_date=None):

        self.__logging = logging.getLogger(__name__)

        self.__req_version = constants.MS_VERSION
        self.__base_endpoint = constants.MS_BASE_URL
        self.__req_timeout = constants.MS_REQ_TIMEOUT

        self.__initial_date = initial_date
        self.__end_date = end_date

        self.__create_directory = constants.MS_DRIVE_CREATE_DIR
        self.__search_directory_file = constants.MS_DRIVE_SEARCH_DIR
        self.__upload_file = constants.MS_DRIVE_UPLOAD_CONTENT
        self.__read_directory = constants.MS_DRIVE_READ_DIR

        self.__ms_access_token = ms_access_token
        self.__req_headers = {"Authorization": "Bearer "+self.__ms_access_token}

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

    def create_directory(self, directory_name):
        crt_resp = {"err_status": True, "response": None}
        try:
            req_url = self.__base_endpoint + self.__req_version + self.__create_directory
            self.__req_headers["Content-Type"] = "application/json"
            req_server = requests.post(req_url, json={
                'name': str(directory_name),
                'folder': {'childCount': 0}
            }, headers=self.__req_headers, timeout=self.__req_timeout).json()

            if constants.RESPONSE_ERROR_KEY not in req_server:
                crt_resp["response"] = req_server["id"]
                crt_resp["err_status"] = False
            else:
                crt_resp["response"] = constants.MS_DRIVE_EXPORT_DIR_ERR
        except Exception as ex:
            self.__logging.exception("Except OneDrive Create DIR: " + str(ex))
            crt_resp["response"] = constants.MS_DRIVE_EXPORT_DIR_EXCEPT
        return crt_resp

    def search_directory(self, directory_name):
        srh_resp = {"err_status": True, "response": None}
        try:
            req_url = self.__base_endpoint + self.__req_version + \
                      self.__search_directory_file.replace('{{search}}', str(directory_name))
            req_server = requests.get(req_url, headers=self.__req_headers, timeout=self.__req_timeout).json()
            if constants.RESPONSE_ERROR_KEY not in req_server:
                for _folder in req_server[constants.RESPONSE_VALUE_KEY]:
                    if _folder["name"] == directory_name:
                        srh_resp["response"] = _folder["id"]
                        srh_resp["err_status"] = False
                        break
            else:
                srh_resp["response"] = constants.MS_DRIVE_EXPORT_DIR_SERC_ERR
        except Exception as ex:
            self.__logging.exception("Except OneDrive Search DIR: " + str(ex))
            srh_resp["response"] = constants.MS_DRIVE_EXPORT_DIR_SERC_EXCEPT
        return srh_resp

    def upload_file(self, directory_name, file_):
        up_resp = {"err_status": True, "response": None}
        try:
            directory_cp = directory_name + '/' + file_["name"]
            req_url = self.__base_endpoint + self.__req_version + self.__upload_file.replace('{{path}}', directory_cp)
            req_url = req_url.replace(' ', '%20')
            self.__req_headers["Content-Type"] = file_["mimetype"]
            self.__req_headers["Slug"] = file_["name"]

            resp_server = requests.put(req_url, data=file_["db_datas"], headers=self.__req_headers).json()
            if constants.RESPONSE_ERROR_KEY in resp_server:
                up_resp["response"] = "Upload file request could not be proceed, Please try again\n" +\
                                   resp_server['error']['message']
            else:
                up_resp["err_status"] = False
        except Exception as ex:
            self.__logging.exception("Exception found while uploading file: " + str(ex))
            up_resp["response"] = constants.MS_DRIVE_FILE_EXPORT_ERR
        return up_resp

    def export_drive_documents(self, res_data):
        self.reset_response()
        try:
            resp = self.search_directory(res_data["res_name"])
            if resp["err_status"]:
                resp = self.create_directory(res_data["res_name"])
            if not resp["err_status"]:
                self.__js_resp["total"] = len(res_data["files"])
                for file in res_data["files"]:
                    _rp = self.upload_file(res_data["res_name"], file)
                    if not _rp["err_status"]:
                        self.__js_resp["success"] += 1
                    else:
                        self.__js_resp["failed"] += 1
                self.__js_resp["err_status"] = False
        except Exception as ex:
            self.__logging.exception("Export Drive Exception: " + str(ex))
            self.__js_resp["response"] = constants.MS_DRIVE_EXP_EXCEPT
        return self.__js_resp

    def read_directory(self, directory_name):
        try:
            req_url = self.__base_endpoint + self.__req_version + self.__read_directory.replace(
                '{{path}}', str(directory_name))
            req_server = requests.get(req_url, headers=self.__req_headers, timeout=self.__req_timeout).json()
            if constants.RESPONSE_ERROR_KEY not in req_server:
                if len(req_server[constants.RESPONSE_VALUE_KEY]) > 0:
                    self.__js_resp["total"] = len(req_server[constants.RESPONSE_VALUE_KEY])
                    self.__js_resp["response"] = req_server[constants.RESPONSE_VALUE_KEY]
                    self.__js_resp["err_status"] = False
                else:
                    self.__js_resp["response"] = constants.MS_DRIVE_FILE_NOT_FND
            else:
                self.__js_resp["response"] = constants.MS_DRIVE_EXPORT_DIR_ERR
        except Exception as ex:
            self.__logging.exception("Read/Import Drive Exception: " + str(ex))
            self.__js_resp["response"] = constants.MS_DRIVE_IMP_SERV_EXCEPT

    def check_file_exists(self, default_env, file, user_rec):
        chk_eir_file = False
        try:
            default_env.cr.execute(
                "select id from " + constants.DB_IR_ATTACHMENT_MODEL + " where name='" + file["name"] +
                "' and mimetype='" + file["file"]["mimeType"] + "'")
            file_rec = default_env.cr.fetchall()
            if file_rec and len(file_rec) > 0:
                for file in file_rec:
                    query = "select * from " + constants.CLASS_IR_ATTACHMENT_REL_MODEL + \
                        " where class_id = " + str(user_rec.id) + " and attachment_id = " + str(file[0])
                    default_env.cr.execute(query)
                    resp = default_env.cr.fetchone()
                    if resp and len(resp) > 0:
                        chk_eir_file = True
        except Exception as ex:
            self.__logging.exception("file search info: " + str(ex))
        return chk_eir_file

    def import_drive_documents(self, self_env, user_record):
        self.reset_response()
        try:
            resp = self.search_directory(user_record.name)
            if resp["err_status"]:
                resp = self.create_directory(user_record.name)
            if not resp["err_status"]:
                self.read_directory(user_record.name)
                if not self.__js_resp["err_status"]:
                    for file_rcd in self.__js_resp["response"]:
                        try:
                            chk_status = self.check_file_exists(self_env, file_rcd, user_record)
                            if not chk_status:
                                file_dwn = requests.get(file_rcd["@microsoft.graph.downloadUrl"])
                                byte_data = base64.b64encode(file_dwn.content)
                                save_rec = self_env[constants.IR_ATTACHMENT_MODEL].create({
                                    'name': file_rcd["name"],
                                    'datas': byte_data,
                                    'mimetype': file_rcd["file"]["mimeType"],
                                    'type': 'binary',
                                    'res_model': constants.CONTACT_TASK_MODEL,
                                    'res_id': 0,
                                })

                                self_env.cr.execute(
                                    "insert into " + constants.CLASS_IR_ATTACHMENT_REL_MODEL +
                                    " (class_id, attachment_id) values (" + str(user_record["id"]) + "," +
                                    str(save_rec.id) + ")")
                                self.__js_resp["success"] += 1
                        except Exception as ex:
                            self.__logging.info("Log >> Read Drive Internal Exception: " + str(ex))
                            self.__js_resp["failed"] += 1
                else:
                    self.__js_resp["response"] = constants.MS_DRIVE_FILE_FETCH_ERR

            else:
                self.__js_resp["response"] = constants.MS_DRIVE_DIR_FETCH_ERR
        except Exception as ex:
            self.__logging.exception("Import Drive Exception: " + str(ex))
            self.__js_resp["response"] = constants.MS_DRIVE_IMP_EXCEPT
        return self.__js_resp
