from . import constants
import requests
import logging
import base64
import json


class Outlook:
    def __init__(self, ms_access_token, default_env, default_email=None, initial_date=None, end_date=None):
        self.__logging = logging.getLogger(__name__)

        self.__ms_access_token = ms_access_token
        self.__default_env = default_env
        self.__default_mail = default_email
        self.__initial_date = initial_date
        self.__end_date = end_date

        self.__req_version = constants.MS_VERSION
        self.__base_endpoint = constants.MS_BASE_URL
        self.__req_timeout = constants.MS_REQ_TIMEOUT
        self.__get_folder = constants.MS_MAILS_FOLDER
        self.__get_all_mails = constants.MS_MAILS_READ_MESSAGE
        self.__email_filter_mails = constants.MS_MAILS_EADDR_FILTER
        self.__send_mail_api = constants.MS_MAILS_SND_MAIL
        self.__send_mail_attach_api = constants.MS_MAILS_SND_MAIL_ATTACH

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

    def send_mail(self, json_params):
        self.reset_response()
        try:
            req_url = self.__base_endpoint + self.__req_version + self.__send_mail_api
            self.__req_headers["Content-Type"] = 'application/json'
            receipt_email, attachments = [], []
            for each in json_params["emails"]:
                receipt_email.append({
                    "emailAddress": {
                        "address": each["email"]
                    }
                })

            for file_attachment in json_params["attachments"]:
                attachments.append({
                    "@odata.type": "#microsoft.graph.fileAttachment",
                    "name": file_attachment["name"],
                    "contentType": file_attachment["mimetype"],
                    "contentBytes": base64.b64encode(file_attachment["db_datas"]).decode()
                })
            mail_params = {
                "message": {
                    "subject": json_params["subject"],
                    "body": {
                        "contentType": "HTML",
                        "content": json_params["content"]
                    },
                    "toRecipients": receipt_email,
                    "attachments": attachments
                },
                "saveToSentItems": "true"
            }
            resp = requests.post(req_url, data=json.dumps(mail_params), headers=self.__req_headers).json()
            if 'error' not in resp:
                self.__js_resp["err_status"] = False
            else:
                self.__js_resp["response"] = resp[constants.RESPONSE_ERROR_KEY][constants.RESPONSE_MESSAGE_KEY]
        except Exception as ex:
            self.__logging.exception("Mail send Exception: " + str(ex))
            self.__js_resp["response"] = constants.MS_MAILS_SEND_MAIL_EXCEPT
        return self.__js_resp

    def get_attachment_file_by_mail(self, mail_id):
        serv_resp = {"err_status": True, "response": None}
        try:
            req_url = self.__base_endpoint + self.__req_version +\
                      self.__send_mail_attach_api.replace("{{mid}}", mail_id)
            resp = requests.get(req_url, headers=self.__req_headers).json()
            if constants.RESPONSE_ERROR_KEY not in resp:
                serv_resp["response"] = resp
                serv_resp["err_status"] = False
            else:
                serv_resp["response"] = constants.MS_MAIL_IMP_SERV_ERR
        except Exception as ex:
            self.__logging.exception("Get mail attachment exception: " + str(ex))
            serv_resp["response"] = constants.MS_MAIL_IMP_SERV_EXCEPT
        return serv_resp

    def get_pagination_mails(self, next_data_link):
        serv_resp = {"err_status": True, "response": None}
        try:
            resp = requests.get(next_data_link, headers=self.__req_headers).json()
            if constants.RESPONSE_ERROR_KEY not in resp:
                serv_resp["response"] = resp
                serv_resp["err_status"] = False
            else:
                serv_resp["response"] = constants.MS_MAIL_IMP_SERV_ERR
        except Exception as ex:
            self.__logging.exception("Outlook Pagination exception: " + str(ex))
            serv_resp["response"] = constants.MS_MAIL_IMP_SERV_EXCEPT
        return serv_resp

    def read_serv_mails(self):
        try:
            req_url = self.__base_endpoint + self.__req_version + self.__get_folder
            fld_resp = requests.get(req_url, headers=self.__req_headers).json()
            if constants.RESPONSE_ERROR_KEY not in fld_resp:
                default_folder_id = None
                for folder in fld_resp[constants.RESPONSE_VALUE_KEY]:
                    if folder["displayName"] == constants.MS_MAILS_DEFAULT_FOLDER:
                        default_folder_id = folder["id"]

                if default_folder_id:
                    req_url += default_folder_id + constants.MS_MAILS_READ_MESSAGE
                    edr_ini, ini = False, False
                    if self.__default_mail:
                        req_url += self.__email_filter_mails.replace('{{email}}', self.__default_mail)
                        edr_ini = True
                    if self.__initial_date or self.__end_date:
                        if edr_ini:
                            req_url += '%20and%20'
                        else:
                            req_url += '?$filter='
                        if self.__initial_date:
                            req_url += 'receivedDateTime%20ge%20' + self.__initial_date.replace(' ', 'T') + 'Z'
                            ini = True
                        if ini:
                            req_url += '%20and%20'
                        if self.__end_date:
                            req_url += 'receivedDateTime%20le%20' + self.__end_date.replace(' ', 'T') + 'Z'

                    resp = requests.get(req_url, headers=self.__req_headers).json()
                    if constants.RESPONSE_ERROR_KEY not in resp:
                        self.__js_resp["response"] = resp[constants.RESPONSE_VALUE_KEY]

                        while ("@odata.nextLink" in resp and resp["@odata.nextLink"]) or \
                                ("response" in resp and "@odata.nextLink" in resp["response"] and
                                 resp["response"]["@odata.nextLink"]):
                            if "response" in resp:
                                next_page_link = resp["response"]["@odata.nextLink"]
                            else:
                                next_page_link = resp["@odata.nextLink"]
                            resp = self.get_pagination_mails(next_page_link)
                            if not resp["err_status"]:
                                self.__js_resp["response"] += resp["response"]["value"]
                            else:
                                break
                        self.__js_resp["err_status"] = False
                    else:
                        self.__js_resp["response"] = resp[constants.RESPONSE_ERROR_KEY][constants.RESPONSE_MESSAGE_KEY]
                else:
                    self.__js_resp["response"] = constants.MS_MAIL_IMP_SERV_FLD_ERR
            else:
                self.__js_resp["response"] = fld_resp[constants.RESPONSE_ERROR_KEY][constants.RESPONSE_MESSAGE_KEY]
        except Exception as ex:
            self.__logging.exception("Serv Mail Import Exception: " + str(ex))
            self.__js_resp["response"] = constants.MS_MAIL_IMP_SERV_EXCEPT

    def import_mails(self):
        self.reset_response()
        try:
            self.read_serv_mails()
            if not self.__js_resp["err_status"]:
                manage_partners = {}
                for mail in self.__js_resp["response"]:
                    sdr_name = mail["sender"]["emailAddress"]["name"]
                    sdr_email = mail["sender"]["emailAddress"]["address"]

                    if sdr_email not in manage_partners:
                        manage_partners.setdefault(sdr_email, None)
                    if not manage_partners[sdr_email]:
                        partner = self.__default_env[constants.CONTACT_TASK_MODEL].search([('email', '=', sdr_email)])
                        if partner and len(partner) > 0:
                            pass
                        else:
                            partner = self.__default_env[constants.OFFICE_CONNECTOR_MODEL].create_contact(
                                sdr_email, sdr_name
                            )
                        if len(partner) > 1:
                            partner = partner[0]
                        manage_partners[sdr_email] = partner.id

                    try:
                        message_rec = self.__default_env[constants.MAIL_MESSAGE_MODEL].create({
                            'subject': mail["subject"],
                            'email_from': sdr_email,
                            'author_id': self.__default_env[constants.RES_USERS_MODEL].partner_id.id,
                            'model': 'res.partner',
                            'message_type': 'notification',
                            'body': mail["body"]["content"],
                            'res_id': manage_partners[sdr_email],
                            'is_internal': True,
                        })
                        mail_attachments = self.get_attachment_file_by_mail(mail_id=mail["id"])
                        if not mail_attachments["err_status"]:
                            for file_attach in mail_attachments["response"]["value"]:
                                save_rec = self.__default_env[constants.IR_ATTACHMENT_MODEL].create({
                                    'name': file_attach["name"],
                                    'datas': file_attach["contentBytes"].encode(),
                                    'mimetype': file_attach["contentType"],
                                    'type': 'binary',
                                    'res_model': constants.CONTACT_TASK_MODEL,
                                    'res_id': 0,
                                })
                                self.__default_env.cr.execute(
                                    "insert into " + constants.MAIL_MESSAGE_ATTACH_MODEL +
                                    " (message_id, attachment_id) values (" + str(message_rec.id) + "," +
                                    str(save_rec.id) + ")")
                        self.__js_resp["success"] += 1
                    except Exception as ex:
                        self.__logging.info("Internal Error Mail Imports: " + str(ex))
                        self.__js_resp["failed"] += 1

                self.__logging.info(manage_partners)
            else:
                self.__js_resp["response"] = constants.MS_MAIL_IMP_SERV_ERR
        except Exception as ex:
            self.__logging.exception("Outer Error Mail Import: " + str(ex))
            self.__js_resp["response"] = constants.MS_MAIL_IMP_EXCEPT
        return self.__js_resp
