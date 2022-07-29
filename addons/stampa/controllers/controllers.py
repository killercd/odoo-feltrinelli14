# -*- coding: utf-8 -*-
from odoo import http
from werkzeug.wrappers import Request, Response
import json
from odoo.addons.queue_job.job import Job
import logging
from functools import wraps
import time
import odoo.addons.stampa.cli.contatti.run_import as contact_import
import odoo.addons.stampa.cli.prodotti.run_import as product_import
import pdb
from pprint import pprint


_logger = logging.getLogger(__name__)

def timeit(func):
    @wraps(func)
    def timeit_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        total_time = end_time - start_time
        print(f'Function {func.__name__}{args} {kwargs} Took {total_time:.4f} seconds')
        return result
    return timeit_wrapper

class ModuloStampa(http.Controller):
    @http.route('/import/autori/', auth='user')
    def index(self, **kw):
        contact_file = "/tmp/contact.csv"
        
        _logger.info("Start import contatti (%s)",contact_file);
        ic = contact_import.ImportContact_14()
        ic.run_batch(http.request.env, contact_file)
        return "OK"
        
    @http.route('/import/product/', auth='user', csrf=False)
    def list(self, **kw):
        product_file = "/tmp/titoli.csv"
        
        _logger.info("Start import autori (%s)",product_file);
        ip = product_import.ImportProducts_14()
        ip.run_batch(http.request.env, product_file)
        return "OK"

    @http.route('/createitem/product/', auth='user', csrf=False)
    def createfile_product(self, **post):
        product_file = "/tmp/titoli.csv"
        if post.get('attachment',False):
            name = post.get('attachment').filename      
            file = post.get('attachment')
            attachment = file.read() 
            with open(product_file,'wb') as fw:
                fw.write(attachment)
        return "OK"


