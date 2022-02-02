import pdb
from odoo import fields, models, api

import logging
import csv
from datetime import datetime
import time

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # 0 Stato
    # 1 Cod.critico
    # 2 Critico
    # 3 Cod.articolo
    # 4 Titolo
    # 5 Autore
    # 6 Num.copie
    # 7 Data invio
    # 8 Note
    # 9 Indirizzo
    # 10 Cap
    # 11 Cod.comune
    # 12 Comune
    # 13 Località
    # 14 Provincia
    # 15 Regione
    # 16 Cod.nazione
    # 17 Nazione
    # 18 Stato fed./contea
    # 19 Cod.tipo invio
    # 20 Telefono
    # 21 Tipo invio
    # 22 Fax
    # 23 Dediche
    # 24 Presso/Att.ne
    # 25 In anticipo
    # 26 Urgente
    # 27 Data ins.
    # 28 Operat. ins.
    # 29 Data agg.
    # 30 Operat. agg.
    # 31 Data Lancio

    def _create_sale_order(self, partner, titolo, row):

        tag_name = u"Lancio del {}".format(row[31].strip())
        tag_id = self.env["send.book"]._get_order_tag(tag_name)
        vals = {
            "partner_id": partner.id,
            "state": "sale",
            "sent": True,
            # 'tag_ids': tag_id,
            "create_ddt": True,
            "urgenza": True if row[26].strip() == "Sì" else False,
            "invio_singolo": False,
            "date_order": datetime.strptime(row[27], "%m/%d/%Y") or False,
            "confirmation_date": datetime.strptime(row[27], "%m/%d/%Y")
            or False,
            "order_line": [
                (
                    0,
                    0,
                    {
                        "name": titolo.name,
                        "product_id": titolo.id,
                        "product_uom_qty": int(row[6]),
                        "product_uom": titolo.uom_id.id,
                        "price_unit": titolo.list_price,
                    },
                )
            ],
            # 'pricelist_id': self.env.ref('product.list0').id,
        }
        # _logger.info(vals)
        # import pdb;pdb.set_trace()
        so = False
        try:
            so = self.env["sale.order"].create(vals)

        except Exception as e:
            _logger.exception(vals)

        return so

    def _get_product_by_isbn(self, isbn):
        titolo = False
        product_template_obj = self.env["product.product"]
        if isbn:
            titolo_id = product_template_obj.search(
                [("barcode", "=", isbn)], limit=1
            ).id
            if titolo_id:
                titolo = product_template_obj.browse(titolo_id)
        return titolo

    def _get_partner_by_codice_critico(self, codice_critico):
        partner = False
        res_partner_obj = self.env["res.partner"]
        if codice_critico:
            partner_id = res_partner_obj.search(
                [("codice_critico", "=", codice_critico)], limit=1
            ).id
            if partner_id:
                partner = res_partner_obj.browse(partner_id)
        return partner

    def _importa_lanci(self, filename):

        reader = csv.reader(filename, delimiter=";")
        reader.next()  # titoli colonne

        countrow = 0
        for row in reader:
            countrow += 1

            if (countrow % 10) == 0:
                _logger.warning("[{}] righe analizzate".format(countrow))

            codice_critico = row[1]

            if codice_critico in self.DUPLICATED:
                _logger.warning(
                    "Trovato critico vecchio [{}] da sostituire con [{}]".format(
                        codice_critico, self.DUPLICATED[codice_critico]
                    )
                )
                codice_critico = self.DUPLICATED[codice_critico]

            partner = self._get_partner_by_codice_critico(codice_critico)
            if not partner:
                _logger.error(
                    "Partner con codice critico [{}] non trovato".format(
                        codice_critico
                    )
                )
                continue

            # cerco il titolo
            isbn = row[3]
            titolo = self._get_product_by_isbn(isbn)
            if not titolo:
                _logger.error(
                    "Titolo non trovato con isbn [{}] non trovato".format(isbn)
                )
                continue

            so = self._create_sale_order(partner, titolo, row)
            if so:
                # _logger.info('Ordine creato con Partner [{}]'.format(partner.name))
                # annullo la picking creata
                for picking in so.picking_ids:
                    picking.action_cancel()

        # _logger.info("Import lanci")

    def _run_job(self, filename):
        _logger.info("job import lanci: START")
        start_time = time.time()

        with open(filename, "rb") as filename:
            self._importa_lanci(filename)

        _logger.info(
            "job import lanci: ENDED in %s seconds ---"
            % (time.time() - start_time)
        )

    DUPLICATED = {
        "98420": "102466",
        "96720": "102788",
        "76825": "93546",
        "63507": "102439",
        "75841": "93917",
        "59084": "103318",
        "58431": "93950",
        "61965": "90504",
        "90239": "103082",
        "77701": "103143",
        "70918": "94175",
        "64512": "102804",
        "59589": "94030",
        "67970": "97758",
        "65945": "88810",
        "58312": "99513",
        "101025": "103714",
        "62642": "70307",
        "75728": "103140",
        "71439": "102917",
        "60114": "98059",
        "97039": "99950",
        "60387": "89276",
        "98126": "98800",
        "1485": "73241",
        "1537": "59639",
        "72942": "102238",
        "72290": "94955",
        "92847": "103549",
        "57146": "98504",
        "76587": "89590",
        "71773": "94736",
        "76853": "98766",
        "73825": "103306",
        "91009": "102798",
        "61344": "99348",
        "70821": "99483",
        "98738": "103313",
        "64148": "102644",
        "75280": "100952",
        "57972": "101307",
        "1405": "73958",
        "94119": "102787",
        "71913": "102787",
        "58988": "93676",
        "71780": "103444",
        "98655": "102824",
        "99518": "103312",
        "76346": "102726",
        "61879": "103560",
        "96430": "103083",
        "61321": "72765",
        "73887": "101069",
        "103203": "103204",
        "58426": "103204",
        "95799": "103551",
        "73927": "87782",
        "76935": "99918",
        "70553": "99918",
        "76191": "94430",
        "102014": "102067",
        "65272": "103773",
        "71781": "101499",
        "59696": "103602",
        "77579": "93547",
        "60645": "93361",
        "60867": "101874",
        "66788": "102919",
        "73728": "98832",
        "77447": "103177",
        "102420": "103219",
        "74945": "94122",
        "72178": "102796",
        "57044": "99262",
        "71555": "100368",
        "94296": "95247",
        "63954": "103261",
        "90426": "103544",
        "61549": "91935",
        "91098": "103412",
        "74632": "102653",
        "65885": "102577",
        "74885": "103352",
        "57502": "103215",
        "75234": "101617",
        "95254": "100168",
        "57771": "96849",
        "57259": "93870",
        "94053": "103086",
        "58447": "103086",
        "98065": "102397",
        "3364": "73370",
        "75716": "99928",
        "98371": "101515",
        "67887": "102710",
        "99234": "101942",
        "75775": "98312",
        "98586": "103278",
        "74057": "103278",
        "74751": "94429",
        "92608": "102734",
        "58052": "91990",
        "77171": "101445",
        "94512": "103576",
        "74060": "94566",
        "78631": "98704",
        "94353": "103267",
        "77122": "100676",
        "59024": "102936",
        "68105": "92922",
        "94340": "97851",
        "99408": "103266",
        "70495": "103266",
        "98044": "103661",
        "71358": "96782",
        "61534": "103490",
        "64113": "103217",
        "62845": "93820",
        "61261": "78823",
        "92220": "98243",
        "66597": "93499",
        "98593": "103580",
        "74811": "88938",
        "76477": "94673",
        "94922": "103563",
        "93288": "101866",
        "63867": "72243",
        "58715": "72243",
        "75516": "92747",
        "57060": "64111",
        "58204": "102144",
        "101572": "103772",
        "74946": "98362",
        "59273": "93374",
        "97108": "100965",
        "57241": "101873",
        "88760": "90775",
        "76574": "93899",
        "65901": "103391",
        "98513": "103106",
        "67975": "103106",
        "95506": "100991",
        "62515": "103459",
        "57635": "102467",
        "94178": "101520",
        "67856": "94092",
        "76693": "90402",
        "59274": "103725",
        "57262": "93834",
        "79302": "102797",
        "98222": "100119",
        "89052": "94511",
        "74449": "94162",
        "97807": "101502",
        "68009": "100172",
        "96459": "103113",
        "99723": "103168",
        "93137": "103793",
        "64160": "103793",
        "58265": "81884",
        "76406": "103786",
        "67381": "96464",
        "99344": "103359",
        "58483": "103676",
        "103304": "103656",
        "65028": "103656",
        "103068": "103202",
        "57623": "103202",
        "77808": "88632",
        "57101": "103603",
        "74662": "102614",
        "71427": "103767",
        "99222": "100958",
        "96581": "103376",
        "96711": "102772",
        "96795": "103042",
    }
