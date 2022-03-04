from ..models.connection import Connection
from ..models.constants import *
from odoo.http import request
from odoo import http
import werkzeug


class TeamsIntegration(http.Controller):
    @http.route(OFFICE_CREDENTIALS_RDT_URI, auth='public')
    def index(self, **kw):

        def_model = request.env[OFFICE_CREDENTIALS_MODEL]
        last_conseq_record = def_model.search([])[DEFAULT_INDEX]
        try:
            if OFFICE_CREDENTIALS_RDT_CODE_FD in str(http.request.httprequest.full_path):
                grant_code = str(http.request.httprequest.full_path).split(OFFICE_CREDENTIALS_RDT_CODE_FD)[1]
                if OFFICE_CREDENTIALS_RDT_CODE_SEPARATOR in grant_code:
                    grant_code = grant_code.split(OFFICE_CREDENTIALS_RDT_CODE_SEPARATOR)[0]
                azure_params = {
                    'redirect_url': last_conseq_record.redirect_url,
                    'client_id': last_conseq_record.client_id,
                    'client_secret': last_conseq_record.client_secret
                }

                conn = Connection(azure_app_cred=azure_params)
                _response = conn.generate_access_token(grant_code=grant_code)
                if not _response["err_status"]:
                    last_conseq_record.grant_code = grant_code
                    last_conseq_record.access_token = conn.get_access_token()
                    last_conseq_record.refresh_token = conn.get_refresh_token()
                    def_model.update(last_conseq_record)
                    return werkzeug.utils.redirect(OFFICE_CREDENTIALS_RDT_ODOO_URI)
                else:
                    return "Connection failed: " + str(_response["response"])
            else:
                return OFFICE_CREDENTIALS_RDT_ERR
        except Exception as ex:
            return "Internal Exception found: " + str(ex)
