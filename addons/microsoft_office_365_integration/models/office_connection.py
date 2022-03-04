import onedrivesdk_fork as onedrivesdk
from onedrivesdk_fork.helpers import GetAuthCodeServer


class OfficeConnection:
    def __init__(self, redirect_url=None, client_id=None, client_secret=None):
        self.__redirect_uri = redirect_url
        self.__client_id = client_id
        self.__client_secret = client_secret
        self.__discovery_uri = 'https://api.office.com/discovery/v2.0/me/services'
        self.__auth_server_url = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
        self.__auth_token_url = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'
        self.__scopes = ['https://graph.microsoft.com/User.Read', 'https://graph.microsoft.com/Files.ReadWrite.All']
        self.__access_token = ''
        self.__grant_code = ''
        self.__refresh_token = ''

    def create_access_token(self):
        http = onedrivesdk.HttpProvider()
        auth = onedrivesdk.AuthProvider(
            http, self.__client_id, auth_server_url=self.__auth_server_url, auth_token_url=self.__auth_token_url,
            scopes=self.__scopes)
        try:
            auth_url = auth.get_auth_url(self.__redirect_uri)
            self.__grant_code = GetAuthCodeServer.get_auth_code(auth_url, self.__redirect_uri)
            auth.authenticate(self.__grant_code, self.__redirect_uri, self.__client_secret)
            self.__access_token = auth.access_token
            self.__refresh_token = auth.refresh_token()
        except Exception as ex:
            print(str(ex))

    def get_access_token(self):
        return self.__access_token

    def get_refresh_token(self):
        return self.__refresh_token
