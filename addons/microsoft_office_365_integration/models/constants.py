####################################################################################################################
# ########################################     Microsoft Graph Basic      ##########################################
####################################################################################################################

MS_AUTH_URL = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
MS_AUTH_EXCODE_URL = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'
MS_BASE_URL = 'https://graph.microsoft.com/'
MS_VERSION = 'v1.0'
MS_REQ_TIMEOUT = 5
MS_SCOPES = [
    'offline_access', 'User.Read', 'Files.ReadWrite.All', 'Mail.Send', 'Mail.ReadWrite', 'Contacts.ReadWrite',
    'Calendars.ReadWrite', 'Tasks.ReadWrite'
]

CONTACT_TASK_MODEL = 'res.partner'
CALENDAR_MODEL = 'calendar.event'
IR_MODEL = 'ir.model'
RES_USERS_MODEL = 'res.users'
MAIL_ACTIVITY_MODEL = 'mail.activity'
MAIL_ACTIVITY_TYPE_MODEL = 'mail.activity.type'
MAIL_MAIL_MODEL = 'mail.mail'
MAIL_MESSAGE_MODEL = 'mail.message'
MAIL_MESSAGE_ATTACH_MODEL = 'message_attachment_rel'
IR_ATTACHMENT_MODEL = 'ir.attachment'
DB_IR_ATTACHMENT_MODEL = 'ir_attachment'
CLASS_IR_ATTACHMENT_REL_MODEL = 'class_ir_attachments_rel'

OFFICE_CREDENTIALS_MODEL = 'office.credentials'
OFFICE_CONNECTOR_MODEL = 'office.connector'
OFFICE_IMPORT_STATS_MODEL = 'office.import.stats'
OFFICE_EXPORT_STATS_MODEL = 'office.export.stats'

OFFICE_CREDENTIALS_RDT_URI = '/office_success'
OFFICE_CREDENTIALS_RDT_ODOO_URI = '/web'
OFFICE_CREDENTIALS_RDT_CODE_FD = 'code='
OFFICE_CREDENTIALS_RDT_CODE_SEPARATOR = '&'
OFFICE_CREDENTIALS_RDT_ERR = "Oops, unable to get authorization information, Please try again"
OFFICE_CREDENTIALS_RDT_URI_ERR = 'Oops, Given redirect url is not supported, Please try again'

RESPONSE_ERROR_KEY = 'error'
RESPONSE_ERR_MESSAGE_KEY = 'err_message'
RESPONSE_MESSAGE_KEY = 'message'
RESPONSE_VALUE_KEY = 'value'

DEFAULT_INDEX = -1
ACCESS_TOKEN_ATTEMPT = 3
TOKEN_ERROR_CODE = '80049228'
TOKEN_ERR_STATUS_CODE = 'InvalidAuthenticationToken'
DEFAULT_ATTACHMENT_PATH = '\\office_attachments\\'

###################################################################################################################
# ###########################################     Contacts Section      ###########################################
###################################################################################################################

MS_CONTACTS_CRUD = '/me/contacts/'

MS_CONTACTS_IMP_EXCEPT = 'Oops, Import Contacts failed, Please try again.'
MS_CONTACTS_IMP_SERV_EXCEPT = 'Oops, Import Contacts from Server failed, Please try again.'

MS_CONTACTS_EXP_EXCEPT = 'Oops, Export Contacts failed, Please try again.'
MS_CONTACTS_EXP_SERV_EXCEPT = 'Oops, Export Contacts to Server failed, Please try again.'
MS_CONTACTS_EXP_NOT_FND = "Oops, Contacts are not found according to date ranges"

###################################################################################################################
# #############################################     Tasks Section      ############################################
###################################################################################################################

MS_TASKS_CRUD = '/me/todo/lists'
MS_TASK_LINK = '/tasks'

MS_TASK_DEFAULT_LIST = 'Tasks'
MS_TASKS_IMP_EXCEPT = 'Oops, Import Tasks failed, Please try again.'
MS_TASKS_IMP_USER_NOT_FND = 'Oops, Unable to find required user info, Please try again.'
MS_TASKS_IMP_SERV_EXCEPT = 'Oops, Import Tasks from Server failed, Please try again.'
MS_TASKS_IMP_SERV_FOLD_NT = 'Oops, Import Tasks from Server, Folder Directory did not found, Please try again.'
MS_TASKS_IMP_SERV_REQ_ERR = 'Oops, Import Tasks from Server Request failed, Please try again.'

MS_TASKS_EXP_EXCEPT = 'Oops, Export Tasks failed, Please try again.'
MS_TASKS_EXP_SERV_EXCEPT = 'Oops, Export Server Tasks Exception, Please try again.'
MS_TASKS_EXP_REC_NOT_FND = 'Oops, Export Tasks Records are not found, Please try again.'
MS_TASKS_EXP_REC_ERR = 'Oops, Export Tasks DLY Record Except, Please try again.'
MS_TASKS_EXP_REC_EXCEPT = 'Oops, Export Tasks DLY Record Except, Please try again.'


###################################################################################################################
# ############################################     Mails Section      #############################################
###################################################################################################################

# MS_MAILS_READ = '/me/messages'
MS_MAILS_FOLDER = "/me/mailFolders/"
MS_MAILS_READ_MESSAGE = "/messages"
MS_MAILS_DEFAULT_FOLDER = "Inbox"
MS_MAILS_SND_MAIL = '/me/sendMail'
MS_MAILS_SND_MAIL_ATTACH = '/me/messages/{{mid}}/attachments'
MS_MAILS_EADDR_FILTER = '/?$filter=from/emailAddress/address+eq+%27{{email}}%27'

MS_MAIL_IMP_SERV_EXCEPT = 'Oops, Import Mails from Server failed, Please try again.'
MS_MAIL_IMP_SERV_ERR = 'Oops, Import Mails failed, Please try again.'
MS_MAIL_IMP_SERV_FLD_ERR = 'Oops, Unable to fetch folder information from server, Please try again.'
MS_MAIL_IMP_EXCEPT = 'Oops, Unable to fetch records from server, Please try again.'
MS_MAILS_SEND_MAIL_EXCEPT = 'Oops, Unable to send mail, Please try again.'


###################################################################################################################
# ##########################################     Calendar Section      ############################################
###################################################################################################################

MS_CALENDAR_CRUD = '/me/events'
MS_CALENDAR_EXP_SERV_EXCEPT = 'Oops, Export Calendar Events Server failed, Please try again.'
MS_CALENDAR_EXP_EXCEPT = 'Oops, Export Calendar Events failed, Please try again.'
MS_CALENDAR_EXP_NT_RCD = 'Oops, Export Calendar Events are not found, Please try again.'
MS_CALENDAR_EXP_NT_DFN = 'Oops, Export Calendar Events records build not proceed, Please try again.'


MS_CALENDAR_IMP_SERV_EXCEPT = 'Oops, Import Calendar Events from Server failed, Please try again.'
MS_CALENDAR_IMP_EXCEPT = 'Oops, Import Calendar Events failed, Please try again.'
MS_CALENDAR_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S.%f'
MS_CALENDAR_PARTNER_REL_ID = 4

###################################################################################################################
# #########################################     OneDrive Section      #############################################
###################################################################################################################

MS_DRIVE_CREATE_DIR = '/me/drive/root/children'
MS_DRIVE_READ_DIR = '/me/drive/root:/{{path}}:/children'
MS_DRIVE_SEARCH_DIR = "/me/drive/root/search(q='{{search}}')"
MS_DRIVE_UPLOAD_CONTENT = '/me/drive/root:/{{path}}:/content'


MS_DRIVE_EXP_SERV_EXCEPT = 'Oops, Export OneDrive Server failed, Please try again.'
MS_DRIVE_EXP_SERV_DIR_ERR = 'Oops, Unable to get directory in Export OneDrive Server, Please try again.'
MS_DRIVE_EXP_EXCEPT = 'Oops, Export OneDrive failed, Please try again.'
MS_DRIVE_EXPORT_DIR_ERR = 'Oops, Unable to create directory in OneDrive, Please try again.'
MS_DRIVE_EXPORT_DIR_EXCEPT = 'Oops, Unable to handle export directory creation in OneDrive, Please try again.'
MS_DRIVE_EXPORT_DIR_SERC_ERR = 'Oops, Unable to search directory in OneDrive, Please try again.'
MS_DRIVE_EXPORT_DIR_SERC_EXCEPT = 'Oops, Unable to handle search directory in OneDrive, Please try again.'

MS_DRIVE_FILE_EXPORT_ERR = 'Oops, Unable to export file to OneDrive, Please try again.'
MS_DRIVE_FILE_NOT_FND = 'Oops, No data files found.'
MS_DRIVE_FILE_FETCH_ERR = "Oops, Unable to fetch internal files"
MS_DRIVE_DIR_FETCH_ERR = "Oops, Unable fetch server directory"

MS_DRIVE_IMP_SERV_EXCEPT = 'Oops, Import Drive from Server failed, Please try again.'
MS_DRIVE_IMP_EXCEPT = 'Oops, Import Drive failed, Please try again.'
MS_DRIVE_OPT_KEY = 'SUC'

###################################################################################################################
# ###########################################      Profile Section      ###########################################
###################################################################################################################
MS_PROFILE_NAME_FD = 'displayName'
MS_PROFILE_EMAIL_FD = 'userPrincipalName'
MS_PROFILE_LINK = '/me'
MS_PROFILE_EXCEPT = "Oops, unable to get profile information, Please try again."

###################################################################################################################
# ########################################      Connection Section      ###########################################
###################################################################################################################

MS_CONN_URL_FAILED = "Oops, unable to generate authorization link."
MS_CONN_URL_EXCEPT = "Oops, unable to generate authorize link, Please try again."
MS_CONN_CRED_FAILED = "Oops, unable to generate credentials."
MS_CONN_CRED_EXCEPT = "Oops, unable to generate credentials, Please try again."
MS_CONN_RAT_FAILED = "Oops, unable to refresh authorization information."
MS_CONN_RAT_EXCEPT = "Oops, unable to refresh authorize info, Please try again."

# System Messages
FAILURE_POP_UP_TITLE = 'System Alert'
AUTH_URL_CREATION_FAILED = 'Oops, system unable to create authorize link'
AUTH_URL_CREATION_EXCEPT = 'Oops, system found exception while creating authorize link'

SYNC_REQ_ERROR = 'Oops, unable to process given request, Please try again'
ACCESS_TOKEN_ERR_REFRESH = 'Oops, unable to refresh authorization information, Please try again'
ACCESS_TOKEN_EXCEPT = 'Oops, unable to get credentials information, Please try again'
ACCESS_TOKEN_CRED_NOT_FND = 'Oops, credentials information not found, Please save credentials before usage'
ACCESS_TOKEN_NOT_FND = 'Oops, authorization information not found, Please authorize account before usage'
ACCESS_TOKEN_INVALID = 'Oops, authorization information is invalid, Please authorize account again'

NO_OPT_SECTION_ERR = 'Oops, no operation is not being selected, Please some operation to proceed.'
SYNC_PROCESS_MSG = "Synchronization process completed"
# DateTime Format
DEFAULT_DATETIME = '2020-01-01 07:00:00'
DEFAULT_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'
DEFAULT_TZ_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S'
INVALID_DATE_RANGES = "Invalid date ranges found, Please correct date ranges."
