from ftplib import FTP
import tempfile

class FtpFeltrinelli(FTP):
    def __init__(self):
        self.host = "pure-ftpd"
        self.user = "username"
        self.passwd = "mypass"
        
        super().__init__(self.host)

    def login(self):
        filename = "/tmp/local_contact.csv"
        super().login(user=self.user, passwd=self.passwd)
        super().retrbinary("RETR " + self._get_contact_filename(), open(filename, 'wb').write)

        f_read = open(filename, 'r')
        return f_read.readlines()
    def _get_contact_filename(self):
        return "contact.csv"
    def _get_product_filename(self):
        return "titoli.csv"
    def download_contacts(self):
        fp = tempfile.NamedTemporaryFile()
        filename = "/tmp/local_contact.csv"
        
        super().retrbinary("RETR " + self._get_contact_filename(), open(filename, 'wb').write)
        
        f_read = open(filename, 'r')
        return f_read.readlines()
    def download_products(self):
        fp = tempfile.NamedTemporaryFile()
        filename = "/tmp/local_product.csv"
        
        super().retrbinary("RETR " + self._get_product_filename(), open(filename, 'wb').write)
        
        f_read = open(filename, 'r')
        return f_read.readlines()