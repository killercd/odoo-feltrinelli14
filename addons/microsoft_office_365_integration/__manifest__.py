# -*- coding: utf-8 -*-
{

    'name': "Odoo Microsoft Office 365 Integration",

    'summary': """
        Odoo Integration with Microsoft Office365 Apps(Outlook, Calender, Task, OneDrive, Contact).""",

    'description': """
        Synchronization of Odoo with Microsoft Office365 Apps.
        Once data is created in Office365 account, then it will be reflected in Odoo by justone click.
    """,

    'author': "WoadSoft",
    'website': "https://woadsoft.com/odoo-integration-with-office-365",
    'category': 'Sale',
    'version': '1.0',
    'depends': ['base', 'mail', 'crm'],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'external_dependencies': {
        'python': [],
    },
    'price': 300,
    'currency': 'EUR',
    'license': 'OPL-1',
    'images':["images/banner.gif"]
}
