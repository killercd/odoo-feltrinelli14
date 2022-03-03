# -*- coding: utf-8 -*-
from odoo import http
from odoo.addons.queue_job.job import Job
import logging
from functools import wraps
import time
from odoo.addons.stampa.cli.contatti.run_import import *
_logger = logging.getLogger(__name__)

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
    @http.route('/import/autori/', auth='public')
    def index(self, **kw):
        #self.writedata()    
        _logger.info('last version')
        # importchimp = ImportFromChimp()
        # importchimp.run(None, None)
        return "last version"
    
    @timeit
    def writedata(self):
        with open("/tmp/a",'w') as op:
            op.write("aaaa\n")
        
    # @http.route('/feltrinelli_reports/feltrinelli_reports/objects/', auth='public')
    # def list(self, **kw):
    #     return http.request.render('feltrinelli_reports.listing', {
    #         'root': '/feltrinelli_reports/feltrinelli_reports',
    #         'objects': http.request.env['feltrinelli_reports.feltrinelli_reports'].search([]),
    #     })

    # @http.route('/feltrinelli_reports/feltrinelli_reports/objects/<model("feltrinelli_reports.feltrinelli_reports"):obj>/', auth='public')
    # def object(self, obj, **kw):
    #     return http.request.render('feltrinelli_reports.object', {
    #         'object': obj
    #     })
