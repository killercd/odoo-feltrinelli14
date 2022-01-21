import functools

import odoo


def get_application_user_id(cr):
    # cr.execute("""select res_id
    #               from ir_model_data where name='application_user'"""\
    #            " and module='onlinestore'")
    # return cr.fetchone()[0]
    return 1


def environmentContextManager(func=None, manage_args_method=""):
    if not func:
        return functools.partial(
            environmentContextManager, manage_args_method=manage_args_method
        )

    @functools.wraps(func)
    def add_env(self, args):
        commandArgs = unknown_args = args
        if manage_args_method:
            commandArgs, unknown_args = getattr(self, manage_args_method)(args)
        odoo.tools.config._parse_config(unknown_args)
        odoo.netsvc.init_logger()
        config = odoo.tools.config
        with odoo.api.Environment.manage() as env:
            _cr = odoo.registry(config["db_name"]).cursor()
            env = odoo.api.Environment(_cr, get_application_user_id(_cr), {})
            # conn, pool = odoo.pooler.get_db_and_pool(config['db_name'])
            func(self, commandArgs, env=env)

    return add_env
