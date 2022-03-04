from odoo import models, fields, api
from . import connection
from . import constants
from . import contacts
from . import outlook
from . import calender
from . import onedrive
from datetime import *
from . import task
import logging
import base64


class OfficeCredentials(models.Model):
    _name = constants.OFFICE_CREDENTIALS_MODEL

    redirect_url = fields.Char(string="Redirect URL", required=True, default=lambda self: self._get_default_url())
    client_id = fields.Char(string="Client ID", required=True, default=lambda self: self._get_default_client_id())
    client_secret = fields.Char(string="Client Secret", required=True,
                                default=lambda self: self._get_default_secret_id())
    access_token = fields.Char(string="Access Token", default=None)
    refresh_token = fields.Char(string="Refresh Token", default=None)
    grant_code = fields.Char(string="Grant Code", default=None)

    def connect(self):
        _logging = logging.getLogger(__name__)

        rep_message = ''
        val_struct = {
            'redirect_url': self.redirect_url,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        try:
            if constants.OFFICE_CREDENTIALS_RDT_URI in self.redirect_url:
                db_cursor = self.env[self._name]
                db_rows = db_cursor.search([])
                if db_rows and len(db_rows) > 0:
                    db_rows[constants.DEFAULT_INDEX].client_id = val_struct["client_id"]
                    db_rows[constants.DEFAULT_INDEX].client_secret = val_struct["client_secret"]
                    db_rows[constants.DEFAULT_INDEX].redirect_url = val_struct["redirect_url"]
                    db_cursor.update(db_rows[constants.DEFAULT_INDEX])
                else:
                    _logging.info("Create CRD record")
                    super().create(val_struct)

                conn = connection.Connection(azure_app_cred=val_struct)
                _response = conn.get_auth_url()
                if not _response["err_status"]:
                    return {
                        'type': 'ir.actions.act_url',
                        'name': "grant_code",
                        'target': 'self',
                        'url': _response["response"],
                    }
                else:
                    rep_message += constants.AUTH_URL_CREATION_FAILED
            else:
                rep_message += constants.OFFICE_CREDENTIALS_RDT_URI_ERR
        except Exception as ex:
            _logging.exception("Exception CRD: " + str(ex))
            rep_message += constants.AUTH_URL_CREATION_EXCEPT
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': constants.FAILURE_POP_UP_TITLE,
                'message': rep_message,
                'sticky': False,
            }
        }

    @api.model
    def _get_default_url(self):
        latest_record = self.env[self._name].search([])
        return latest_record[constants.DEFAULT_INDEX].redirect_url if len(latest_record) > 0 else ''

    @api.model
    def _get_default_client_id(self):
        latest_record = self.env[self._name].search([])
        return latest_record[constants.DEFAULT_INDEX].client_id if len(latest_record) > 0 else ''

    @api.model
    def _get_default_secret_id(self):
        latest_record = self.env[self._name].search([])
        return latest_record[constants.DEFAULT_INDEX].client_secret if len(latest_record) > 0 else ''

    def get_office_credentials(self):
        cred_response = {}
        try:
            db_rows = self.env[self._name].search([])
            if db_rows and len(db_rows) > 0:
                cred_response["client_id"] = db_rows[constants.DEFAULT_INDEX].client_id
                cred_response["client_secret"] = db_rows[constants.DEFAULT_INDEX].client_secret
                cred_response["redirect_url"] = db_rows[constants.DEFAULT_INDEX].redirect_url
            else:
                cred_response[constants.RESPONSE_ERR_MESSAGE_KEY] = constants.MS_CONN_CRED_FAILED
                cred_response[constants.RESPONSE_ERROR_KEY] = "Credentials are not found"
        except Exception as ex:
            cred_response[constants.RESPONSE_ERROR_KEY] = str(ex)
            cred_response[constants.RESPONSE_ERR_MESSAGE_KEY] = constants.MS_CONN_CRED_EXCEPT
        return cred_response


class OfficeSync(models.Model):
    _name = constants.OFFICE_CONNECTOR_MODEL

    import_contact = fields.Boolean(default=False)
    export_contact = fields.Boolean(default=False)
    import_calender = fields.Boolean(default=False)
    export_calender = fields.Boolean(default=False)

    import_task = fields.Boolean(default=False)
    export_task = fields.Boolean(default=False)
    import_email = fields.Boolean(default=False)

    import_data_stats = fields.One2many(constants.OFFICE_IMPORT_STATS_MODEL, inverse_name="connector")
    export_data_stats = fields.One2many(constants.OFFICE_EXPORT_STATS_MODEL, inverse_name="connector")
    custom_from_datetime = fields.Datetime('From Date', required=False, readonly=False, select=True,
                                           default=lambda self: (fields.datetime.now() - timedelta(hours=1)))
    custom_to_datetime = fields.Datetime('To Date', required=False, readonly=False, select=True,
                                         default=lambda self: (fields.datetime.now() + timedelta(hours=1)))

    def create_contact(self, contact_email, name=None):
        contact_rec = self.env[constants.CONTACT_TASK_MODEL].create({
            'name': name if name else contact_email.split('@')[0],
            'email': contact_email
        })
        return contact_rec

    def synchronize(self):
        _logging = logging.getLogger(__name__)

        pop_up_message, date_error_chk = "", False
        import_chk_status, export_chk_status = False, False
        imp_contact, imp_calendar, imp_task, imp_mail = 0, 0, 0, 0
        exp_contact, exp_calendar, exp_task = 0, 0, 0
        try:
            if self.custom_from_datetime > self.custom_to_datetime:
                date_error_chk = True

            if not date_error_chk:
                credentials = self.env[constants.OFFICE_CREDENTIALS_MODEL].get_office_credentials()
                if constants.RESPONSE_ERROR_KEY not in credentials and \
                        constants.RESPONSE_ERR_MESSAGE_KEY not in credentials:
                    connect = connection.Connection(azure_app_cred=credentials, default_env=self.env)
                    conn_response = connect.get_msv_access_token()
                    if not conn_response["err_status"]:

                        if self.import_contact or self.export_contact:
                            _contacts = contacts.Contacts(
                                ms_access_token=conn_response["response"], default_env=self.env,
                                initial_date=str(self.custom_from_datetime), end_date=str(self.custom_to_datetime))
                            if self.import_contact:
                                contact_response = _contacts.import_contacts()
                                if not contact_response["err_status"]:
                                    imp_contact += contact_response["success"]
                            if self.export_contact:
                                contact_response = _contacts.export_contacts()
                                if not contact_response["err_status"]:
                                    exp_contact += contact_response["success"]

                        if self.import_calender or self.export_calender:
                            _calendar = calender.Calender(
                                ms_access_token=conn_response["response"], default_env=self.env,
                                default_profile=conn_response["addons"], initial_date=str(self.custom_from_datetime),
                                end_date=str(self.custom_to_datetime))
                            if self.import_calender:
                                calendar_response = _calendar.import_events()
                                if not calendar_response["err_status"]:
                                    imp_calendar += calendar_response["success"]
                            if self.export_calender:
                                calendar_response = _calendar.export_events()
                                if not calendar_response["err_status"]:
                                    exp_calendar += calendar_response["success"]

                        if self.import_task or self.export_task:
                            _task = task.Task(
                                ms_access_token=conn_response["response"], default_env=self.env,
                                default_profile=conn_response["addons"], admin_user_email=self.env.user.email,
                                initial_date=str(self.custom_from_datetime), end_date=str(self.custom_to_datetime),
                                folder=None)
                            if self.import_task:
                                task_response = _task.import_tasks()
                                if not task_response["err_status"]:
                                    imp_task += task_response["success"]
                            if self.export_task:
                                task_response = _task.export_tasks()
                                if not task_response["err_status"]:
                                    exp_task += task_response["success"]

                        if self.import_email:
                            _outlook = outlook.Outlook(
                                ms_access_token=conn_response["response"], default_env=self.env, default_email=None,
                                initial_date=str(self.custom_from_datetime), end_date=str(self.custom_to_datetime))
                            outlook_response = _outlook.import_mails()
                            if not outlook_response["err_status"]:
                                imp_mail += outlook_response["success"]

                        if self.import_contact or self.import_calender or self.import_email or self.import_task:
                            if imp_mail or imp_task or imp_contact or imp_calendar:
                                self.env[constants.OFFICE_IMPORT_STATS_MODEL].create({
                                    'email': imp_mail, 'task': imp_task, 'calender': imp_calendar,
                                    'contact': imp_contact, 'connector': self.id
                                })
                            if pop_up_message == "":
                                pop_up_message += constants.SYNC_PROCESS_MSG
                            import_chk_status = True

                        if self.export_contact or self.export_calender or self.export_task:
                            if exp_task or exp_calendar or exp_contact:
                                self.env[constants.OFFICE_EXPORT_STATS_MODEL].create({
                                    'task': exp_task, 'calender': exp_calendar, 'contact': exp_contact,
                                    'connector': self.id
                                })
                            if pop_up_message == "":
                                pop_up_message += constants.SYNC_PROCESS_MSG
                            export_chk_status = True

                        if not export_chk_status and not import_chk_status:
                            pop_up_message = constants.NO_OPT_SECTION_ERR
                    else:
                        pop_up_message += conn_response["response"]
                else:
                    pop_up_message += credentials["err_message"]
                    _logging.info("Error while Sync: " + credentials["error"])
            else:
                pop_up_message += constants.INVALID_DATE_RANGES
        except Exception as ex:
            _logging.exception("Sync Exception: " + str(ex))
            pop_up_message += constants.SYNC_REQ_ERROR
        return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': "System Notification",
                    'message': pop_up_message,
                    'sticky': False,
                }
            }

    def import_history_action(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': constants.OFFICE_IMPORT_STATS_MODEL,
            'view_mode': 'tree',
            'context': {'no_breadcrumbs': True}
        }

    def export_history_action(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': constants.OFFICE_EXPORT_STATS_MODEL,
            'view_mode': 'tree',
            'context': {'no_breadcrumbs': True}
        }


class MailMailContact(models.Model):
    _inherit = constants.MAIL_MAIL_MODEL

    def custom_send_mail(self, js_data):
        resp = {"err_status": True, "response": None}
        try:
            credentials = self.env[constants.OFFICE_CREDENTIALS_MODEL].get_office_credentials()
            if constants.RESPONSE_ERROR_KEY not in credentials and \
                    constants.RESPONSE_ERR_MESSAGE_KEY not in credentials:
                conn = connection.Connection(azure_app_cred=credentials, default_env=self.env)
                response = conn.get_msv_access_token()
                if not response["err_status"]:
                    _outlook = outlook.Outlook(ms_access_token=response["response"], default_env=self.env)
                    serv_response = _outlook.send_mail(json_params=js_data)
                    if not serv_response["err_status"]:
                        resp["err_status"] = False
                    else:
                        resp = "Log >> " + str(serv_response["response"])
                else:
                    resp = "Log >> " + str(response["response"])
            else:
                resp = "Log >> " + str(credentials[constants.RESPONSE_ERR_MESSAGE_KEY])
        except Exception as ex:
            resp["response"] = "Log >> Oops, Mail could not be sent: " + str(ex)
        return resp

    @api.model
    def create(self, vals):
        _log = logging.getLogger(__name__)

        mail_rec = super(MailMailContact, self).create(vals)
        pop_message = ""
        try:
            _js_mail_data = {
                "subject": vals["subject"],
                "content": vals["body_html"],
                "emails": [],
                "attachments": []
            }

            query = "select res_partner_id from mail_mail_res_partner_rel where mail_mail_id=" + str(mail_rec.id)
            self.env.cr.execute(query)
            partner = self.env.cr.fetchone()
            if partner or len(partner) > 0:
                _contact = self.env[constants.CONTACT_TASK_MODEL].search([("id", "=", partner[0])])
                if _contact and len(_contact) > 0:
                    _js_mail_data["emails"].append({"email": _contact.email})

                    at_query = "select attachment_id from " + constants.MAIL_MESSAGE_ATTACH_MODEL + \
                               " where message_id=" + str(mail_rec.mail_message_id.id)
                    self.env.cr.execute(at_query)
                    mail_attachment = self.env.cr.fetchall()
                    if mail_attachment and len(mail_attachment) > 0:
                        for attachment in mail_attachment:
                            file_attach = self.env[constants.IR_ATTACHMENT_MODEL].search([("id", "=", attachment[0])])
                            decoded_data = base64.b64decode(file_attach.datas)
                            _js_mail_data["attachments"].append({
                                "id": file_attach.id,
                                "name": file_attach.name,
                                "mimetype": file_attach.mimetype,
                                "db_datas": decoded_data
                            })
                    _response = self.custom_send_mail(_js_mail_data)
                    _log.info(_response)
                    if not _response["err_status"]:
                        pop_message += "Log >> Mail sent successfully"
                    else:
                        pop_message += "Log >> " + str(_response["response"])
                else:
                    pop_message += "Log >> Oops, Unable to get sender information."
        except Exception as ex:
            pop_message += "Log >> Oops, Exception found, " + str(ex)
        _log.info(pop_message)
        return mail_rec


class OneDriveConnect(models.Model):
    _inherit = constants.CONTACT_TASK_MODEL

    attachment_ids = fields.Many2many(
        constants.IR_ATTACHMENT_MODEL, constants.CLASS_IR_ATTACHMENT_REL_MODEL,
        'class_id', 'attachment_id', 'Attachments')

    def one_drive_upload_btn(self):
        _log = logging.getLogger(__name__)

        pop_message = ""
        r_partner = self.env[constants.CONTACT_TASK_MODEL].search([('id', '=', self.id)])
        file_records = {
            'res_partner_id': self.id,
            'res_name': r_partner.name,
            'files': []
        }
        for attachment in self.attachment_ids:
            try:
                decoded_data = base64.b64decode(attachment.datas)
                file_records["files"].append({
                    "id": attachment.id,
                    "name": attachment.name,
                    "mimetype": attachment.mimetype,
                    "db_datas": decoded_data
                })
            except Exception as ex:
                _log.info("Log >> File attachment info: " + str(ex))

        credentials = self.env[constants.OFFICE_CREDENTIALS_MODEL].get_office_credentials()
        if constants.RESPONSE_ERROR_KEY not in credentials and constants.RESPONSE_ERR_MESSAGE_KEY not in credentials:
            connect = connection.Connection(azure_app_cred=credentials, default_env=self.env)
            conn_response = connect.get_msv_access_token()
            if not conn_response["err_status"]:
                _onedrive = onedrive.OneDrive(ms_access_token=conn_response["response"])
                _dr_response = _onedrive.export_drive_documents(res_data=file_records)
                _log.info(_dr_response)
                if not _dr_response["err_status"]:
                    pop_message += "Files uploaded successfully: " + constants.MS_DRIVE_OPT_KEY
                else:
                    pop_message += str(_dr_response["response"])
            else:
                pop_message += conn_response["response"]
        else:
            pop_message += credentials[constants.RESPONSE_ERR_MESSAGE_KEY]
        if constants.MS_DRIVE_OPT_KEY in pop_message:
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': "System Notification",
                    'message': pop_message,
                    'sticky': False,
                }
            }

    def one_drive_download_btn(self):
        _log = logging.getLogger(__name__)

        pop_message = ""
        r_partner = self.env[constants.CONTACT_TASK_MODEL].search([('id', '=', self.id)])
        credentials = self.env[constants.OFFICE_CREDENTIALS_MODEL].get_office_credentials()
        if constants.RESPONSE_ERROR_KEY not in credentials and constants.RESPONSE_ERR_MESSAGE_KEY not in credentials:
            connect = connection.Connection(azure_app_cred=credentials, default_env=self.env)
            conn_response = connect.get_msv_access_token()
            if not conn_response["err_status"]:
                _onedrive = onedrive.OneDrive(ms_access_token=conn_response["response"])
                _dr_response = _onedrive.import_drive_documents(
                    self_env=self.env, user_record=r_partner)
                if not _dr_response["err_status"]:
                    pop_message += "Files downloaded successfully: " + constants.MS_DRIVE_OPT_KEY
                else:
                    pop_message += str(_dr_response["response"])
            else:
                pop_message += conn_response["response"]
        else:
            pop_message += credentials["err_message"]
        if constants.MS_DRIVE_OPT_KEY in pop_message:
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': "System Notification",
                    'message': pop_message,
                    'sticky': False,
                }
            }


class ImportDataStats(models.Model):
    _name = constants.OFFICE_IMPORT_STATS_MODEL

    connector = fields.Many2one(constants.OFFICE_CONNECTOR_MODEL)
    calender = fields.Integer()
    contact = fields.Integer()
    email = fields.Integer()
    task = fields.Integer()


class ExportDataStats(models.Model):
    _name = constants.OFFICE_EXPORT_STATS_MODEL

    connector = fields.Many2one(constants.OFFICE_CONNECTOR_MODEL)
    calender = fields.Integer()
    contact = fields.Integer()
    task = fields.Integer()
