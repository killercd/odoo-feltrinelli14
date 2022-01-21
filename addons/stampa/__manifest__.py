{
    "name": "Ufficio Stampa",
    "summary": "Personalizzazioni per Uffico Stampa Feltrinelli",
    "description": "Personalizzazioni per Uffico Stampa Feltrinelli",
    "author": "Link IT Srl",
    "website": "http://linkgroup.it/",
    "category": "LinkIT",
    "version": "13.0.1.0.0",
    "depends": [
        "contacts",
        "crm",
        "mail",
        # "l10n_it_base_location_geonames_import",
        # "l10n_it_ddt",
        "stock",
        "sale",
        "partner_firstname",
        "queue_job",
        "queue_job_cron"
    ],
    # always loaded
    "data": [
        "security/ir.model.access.csv",
        "product/views/product_views.xml",
        "product/views/send_book.xml",
        "product/wizard/ordini_libri_view.xml",
        "sale/views/sale_views.xml",
        "sale/views/default.xml",
        # FIXV14 # serve ancora questo wizard ? -->"sale/wizard/tag_wizard_views.xml",
    ],
    "installable": True,
    "auto_install": False,
    "application": False,
}
