{
    "name": "Ufficio Stampa",
    "summary": "Personalizzazioni per Uffico Stampa Feltrinelli",
    "description": "Personalizzazioni per Uffico Stampa Feltrinelli",
    "author": "NTT DATA, Marco Di Francesco",
    "website": "",
    "category": "LinkIT",
    "version": "13.0.1.0.0",
    "depends": [
        "contacts",
        "crm",
        "sale_crm",
        "mail",
        "stock",
        "sale",
        "sale_management",
        "partner_firstname",
        "queue_job",
        "queue_job_cron",
        "sh_message",
        "opencloud_massive_tag_update",
        "mail",
        "product",
        "sale_management",
        "feltrinelli_reports",
        "snailmail_account_followup",
        "custom_feltrinelli"
        # "base_location"
    ],
    # always loaded
    "data": [
        "security/ir.model.access.csv",
        "product/views/product_views.xml",
        "product/views/send_book.xml",
        "product/wizard/ordini_libri_view.xml",
        "sale/views/sale_views.xml",
        "sale/views/default.xml",
        "sale/views/queue_job.xml"
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
}
