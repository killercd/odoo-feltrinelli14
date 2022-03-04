from datetime import datetime
from . import constants
from dateutil import tz
import requests
import logging
import json
import pytz


class Calender:
    def __init__(self, ms_access_token, default_env, default_profile=None, initial_date=None, end_date=None):
        self.__logging = logging.getLogger(__name__)

        self.__ms_access_token = ms_access_token
        self.__default_env = default_env
        self.__default_profile = default_profile
        self.__initial_date = initial_date
        self.__end_date = end_date

        self.__req_version = constants.MS_VERSION
        self.__base_endpoint = constants.MS_BASE_URL
        self.__req_timeout = constants.MS_REQ_TIMEOUT
        self.__event = constants.MS_CALENDAR_CRUD
        self.__from_zone = tz.tzutc()
        self.__to_zone = tz.tzlocal()

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

    def read_serv_events(self):
        try:
            req_url = self.__base_endpoint + self.__req_version + self.__event
            ini = False
            if self.__initial_date or self.__end_date:
                req_url += '/?$filter='
                if self.__initial_date:
                    req_url += "createdDateTime%20ge%20" + self.__initial_date.replace(' ', 'T') + "Z"
                    ini = True
                if self.__end_date:
                    if ini:
                        req_url += '%20and%20'
                    req_url += "createdDateTime%20le%20" + self.__end_date.replace(' ', 'T') + "Z"

            sr_resp = requests.get(req_url, headers=self.__req_headers).json()
            if constants.RESPONSE_ERROR_KEY not in sr_resp:
                self.__js_resp["response"] = sr_resp[constants.RESPONSE_VALUE_KEY]
                self.__js_resp["total"] = len(sr_resp[constants.RESPONSE_VALUE_KEY])
                self.__js_resp["err_status"] = False
            else:
                self.__js_resp["response"] = sr_resp[constants.RESPONSE_ERROR_KEY][constants.RESPONSE_MESSAGE_KEY]
        except Exception as ex:
            self.__logging.exception("Calender Serv Read Exception: " + str(ex))
            self.__js_resp["response"] = constants.MS_CALENDAR_IMP_SERV_EXCEPT

    def import_events(self):
        self.reset_response()
        try:
            self.read_serv_events()
            if not self.__js_resp["err_status"]:
                for event in self.__js_resp["response"]:
                    calendar_rec = self.__default_env[constants.CALENDAR_MODEL].search([
                        ('name', '=', event["subject"])
                    ])
                    if len(calendar_rec) == 0:
                        try:
                            attendees = [user["emailAddress"]["address"] for user in event["attendees"]]
                            timezone = pytz.timezone(event["start"]["timeZone"])

                            _start_date = event["start"]["dateTime"][:-1]
                            _sdte = datetime.strptime(_start_date, constants.MS_CALENDAR_DATE_FORMAT)
                            _start_datetime = timezone.localize(_sdte)
                            _utc = _start_datetime.replace(tzinfo=self.__from_zone)
                            _stt_date = _utc.astimezone(self.__to_zone).replace(tzinfo=None)

                            _end_date = event["end"]["dateTime"][:-1]
                            _edte = datetime.strptime(_end_date, constants.MS_CALENDAR_DATE_FORMAT)
                            _end_datetime = timezone.localize(_edte)
                            _utc = _end_datetime.replace(tzinfo=self.__from_zone)
                            _ed_date = _utc.astimezone(self.__to_zone).replace(tzinfo=None)

                            _partner_ids = []
                            for participant_email in attendees:
                                partner = self.__default_env[constants.CONTACT_TASK_MODEL].search([
                                    ("email", '=', participant_email)
                                ])
                                if partner and len(partner) > 0:
                                    _partner_ids.append((constants.MS_CALENDAR_PARTNER_REL_ID, partner[0].id))
                                else:
                                    partner = self.__default_env[constants.OFFICE_CONNECTOR_MODEL].create_contact(
                                        participant_email)
                                    _partner_ids.append((constants.MS_CALENDAR_PARTNER_REL_ID, partner.id))

                            self.__default_env[constants.CALENDAR_MODEL].create({
                                "name": event["subject"],
                                "description": event["body"]["content"],
                                "start": _stt_date,
                                "partner_ids": _partner_ids if len(_partner_ids) > 0 else [],
                                "stop": _ed_date
                            })
                            self.__js_resp["success"] += 1
                        except Exception as ex:
                            self.__js_resp["failed"] += 1
                            self.__logging.info("Calendar Internal Import Exception: " + str(ex))
        except Exception as ex:
            self.__logging.exception("Calendar Import Exception: " + str(ex))
            self.__js_resp["response"] = constants.MS_CALENDAR_IMP_EXCEPT
        return self.__js_resp

    def chk_serv_event(self, event_rec):
        chk_response = {"err_status": True, "response": None}
        try:
            req_url = self.__base_endpoint + self.__req_version + self.__event
            req_url += "?$filter=subject%20eq%20'" + event_rec["name"].replace(' ', '%20') + "'"
            self.__req_headers['Content-Type'] = 'application/json'
            sr_resp = requests.get(req_url, headers=self.__req_headers).json()
            if constants.RESPONSE_ERROR_KEY not in sr_resp:
                if len(sr_resp[constants.RESPONSE_VALUE_KEY]) > 0:
                    chk_response["err_status"] = False
                else:
                    chk_response["response"] = "Event record did not exist."
            else:
                chk_response["response"] = sr_resp[constants.RESPONSE_ERROR_KEY][constants.RESPONSE_MESSAGE_KEY]
        except Exception as ex:
            chk_response["response"] = "Check event failed: " + str(ex)
        return chk_response

    def write_serv_event(self, _event_datas):
        try:
            req_url = self.__base_endpoint + self.__req_version + self.__event
            self.__req_headers['Content-Type'] = 'application/json'
            default_app_sam = [{
                "emailAddress": {
                    "address": self.__default_profile[constants.MS_PROFILE_NAME_FD],
                    "name": self.__default_profile[constants.MS_PROFILE_EMAIL_FD]
                },
                "type": "required"
            }]

            for _event_obj in _event_datas:
                chk_event_resp = self.chk_serv_event(_event_obj)
                if chk_event_resp["err_status"]:
                    attends_tmp = []
                    for attend in _event_obj["attendees"]:
                        attends_tmp.append({
                            "emailAddress": {
                                "address": attend["email"],
                                "name": attend["name"]
                            },
                            "type": "required"
                        })

                    json_params = {
                        "subject": _event_obj["name"],
                        "body": {
                            "contentType": "HTML",
                            "content": _event_obj["desc"]
                        },
                        "start": {
                            "dateTime": str(_event_obj["start"]),
                            "timeZone": "UTC"
                        },
                        "end": {
                            "dateTime": str(_event_obj["stop"]),
                            "timeZone": "UTC"
                        },
                        "attendees": attends_tmp if len(attends_tmp) > 0 else default_app_sam,
                        "allowNewTimeProposals": True,
                    }
                    sr_resp = requests.post(req_url, data=json.dumps(json_params), headers=self.__req_headers).json()
                    if constants.RESPONSE_ERROR_KEY not in sr_resp:
                        self.__js_resp["success"] += 1
                    else:
                        self.__js_resp["failed"] += 1
                        self.__logging.info("Export Event Serv Internal Error: " +
                                            sr_resp[constants.RESPONSE_ERROR_KEY][constants.RESPONSE_MESSAGE_KEY])
        except Exception as ex:
            self.__logging.exception("Calendar Export SERV Exception: " + str(ex))
            self.__js_resp["response"] = constants.MS_CALENDAR_EXP_SERV_EXCEPT

    def export_events(self):
        self.reset_response()
        try:
            json_calendar, query_params = [], []
            if self.__initial_date and self.__end_date:
                query_params.append('&')
            if self.__initial_date:
                query_params.append(('create_date', '>=', str(self.__initial_date).replace('T', ' ')))
            if self.__end_date:
                query_params.append(('create_date', '<=', str(self.__end_date).replace('T', ' ')))

            _db_calendar = self.__default_env[constants.CALENDAR_MODEL].search(query_params)
            if _db_calendar and len(_db_calendar) > 0:
                for _cal_event in _db_calendar:
                    _attends = []
                    for _attend in _cal_event.partner_ids:
                        _attends.append({
                            "name": _attend.name,
                            "email": _attend.email
                        })
                    json_calendar.append({
                        "name": _cal_event.name,
                        "desc": _cal_event.description,
                        "start": str(_cal_event.start).replace(' ', 'T'),
                        "stop": str(_cal_event.stop).replace(' ', 'T'),
                        "attendees": _attends
                    })

                if len(json_calendar) > 0:
                    self.write_serv_event(_event_datas=json_calendar)
                    self.__js_resp["total"] = len(json_calendar)
                    self.__js_resp["err_status"] = False
                else:
                    self.__js_resp["response"] = constants.MS_CALENDAR_EXP_NT_DFN
            else:
                self.__js_resp["response"] = constants.MS_CALENDAR_EXP_NT_RCD
        except Exception as ex:
            self.__logging.exception("Export Calendar Event Exception: " + str(ex))
            self.__js_resp["response"] = constants.MS_CALENDAR_EXP_EXCEPT
        return self.__js_resp
