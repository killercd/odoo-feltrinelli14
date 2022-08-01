from __future__ import print_function
from ast import While

import logging
import argparse
from itertools import islice, chain
import csv
import pdb
import unicodedata
import re
from contextlib import contextmanager
from datetime import datetime
import time

import attr
from builtins import str

from odoo.cli import Command
from odoo.addons.stampa.cli.run import environmentContextManager
from odoo.addons.stampa.product.models import *


logger = logging.getLogger(__name__)

BATCH = 10
ENC = "utf-8"
COLLANE_COLOR = 7
DELIMITER = ";"


class LoadingException(Exception):
    pass


@contextmanager
def cursor(env):    
    try:
        yield env.cr
    finally:
        env.cr.close()


def slugify(value):
    if not isinstance(value, unicode):
        value = value.decode(ENC, "ignore")
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore")
    value = re.sub("[^/\w\s@-]", "", value).strip().lower()
    return re.sub("[-\s/]+", "_", value)


def external_id(target, field):
    # import pdb; pdb.set_trace()
    key = slugify(field)
    ext_id = "feltricrm.%s_%s" % (target, key)
    return ext_id


def result_generator(cursor, recordnum=BATCH):
    while True:
        result = cursor.fetchmany(recordnum)
        if not result:
            break
        yield result


def batch_generator(iterable, recordnum=BATCH):
    source = iter(iterable)
    while True:
        batchiter = islice(source, recordnum)
        yield list(chain([batchiter.next()], batchiter))


def utf_reader(infile):
    reader = csv.reader(infile, delimiter=DELIMITER)
    for row in reader:
        yield [unicode(cell, "utf-8", "replace") for cell in row]


@attr.s
class Product(object):
    name = attr.ib()
    id = attr.ib()
    barcode = attr.ib()
    data_uscita = attr.ib()
    data_cedola = attr.ib()
    nome_cedola = attr.ib()
    redazione = attr.ib()
    collana_id = attr.ib()
    marchio_editoriale = attr.ib(default=None)
    book_type = attr.ib(default=None)
    in_magazzino = attr.ib(default=None)
    autori_id = attr.ib(default=None)
    curatori_id = attr.ib(default=None)
    prefatori_id = attr.ib(default=None)
    traduttori_id = attr.ib(default=None)
    illustratori_id = attr.ib(default=None)
    type = attr.ib(default="product")
    sale_ok = attr.ib(default="true")
    purchase_ok = attr.ib(default="true")


@attr.s
class Category(object):
    name = attr.ib()
    id = attr.ib()
    color = attr.ib(default=None)
    parent_id = attr.ib(default=None)


@attr.s
class Collana(object):
    name = attr.ib()
    id = attr.ib()


class ImportProducts(Command):
    def manage_args(self, args):
        # import pdb;pdb.set_trace()
        parser = argparse.ArgumentParser()
        parser.add_argument("--debug", action="store_true")
        parser.add_argument("--categories", action="store_true")
        parser.add_argument("--collane")
        parser.add_argument("--filename")
        parser.add_argument("--lanci")

        # parser.add_argument("infile",
        #                    type=argparse.FileType('r'))
        args, unknown = parser.parse_known_args(args)
        return args, unknown

    def set_ids_check_results(self, results):
        
        self.errors = results["messages"]
        self.ids = results["ids"] or []
        if self.errors:
            logger.error("Errore: %s", self.errors)
            self.rollback()
        else:
            self.commit()
        return self.ids

    def rollback(self):
        self.env.cr.rollback()

    def commit(self):
        self.env.cr.commit()

    def get_category_names(self, field):
        # import pdb; pdb.set_trace()
        names = field.split(";")
        # logger.info(" get_category_names names 1: %s", names)
        names = map(lambda x: x.strip().title(), names)
        # logger.info("get_category_names names 2: %s", names)
        return filter(None, names)

    def get_collane(self, infile):
        # import pdb; pdb.set_trace()
        reader = utf_reader(infile)
        # reader.next()
        found = set()
        logger.debug(" get_collane ")
        for line in reader:
            # import pdb; pdb.set_trace()
            collana_id = line[4].strip()
            collana = line[5].strip()
            # collana_id = line[0].strip()
            # collana = line[3].strip()

            if not collana or collana in found:
                continue

            if collana:
                found.add(collana_id)

            yield Collana(
                name=collana,
                id=external_id("collane", collana_id),
            )

    # ===========================================================================
    # def get_category_collane(self):
    #     return Category(name="Collane",
    #                     id=external_id('categorie', 'collane'))
    # ===========================================================================

    def get_external_ids(self, prefix, values):
        # import pdb; pdb.set_trace()
        logger.debug("get_external_ids")
        categories = self.get_category_names(values)
        logger.debug("categories: %s", categories)
        if not categories:
            return None
        cat_ids = [external_id(prefix, cat) for cat in categories]
        logger.debug("cat_ids: %s", cat_ids)
        category_id = ",".join(cat_ids)
        logger.debug("category_id: %s", category_id)
        return category_id

    def get_products(self, infile):
        reader = utf_reader(infile)
        reader.next()  # skip first line
        # import pdb;pdb.set_trace()
        for line in reader:
            # id_gpe = line[0]
            isbn13 = line[1]
            titolo = line[2].strip()
            # sottotitolo = line[3].strip()
            collana_id = line[4].strip()
            collana = line[5].strip()
            data_uscita = line[6]
            in_magazzino = line[7]
            tipo = line[8].title()
            redazione = line[9]
            marchio = line[10].strip().title()
            autori = line[11]
            curatori = line[12]
            prefatori = line[13]
            traduttori = line[14]
            illustratori = line[15]
            nome_cedola = line[16]
            data_cedola = line[17]
            id = external_id("libri", isbn13)

            ##collana_id = collana_id
            collana_id = self.get_external_ids("collane", collana_id)
            autori_id = self.get_external_ids("autori", autori)
            curatori_id = self.get_external_ids("autori", curatori)
            prefatori_id = self.get_external_ids("autori", prefatori)
            traduttori_id = self.get_external_ids("autori", traduttori)
            illustratori_id = self.get_external_ids("autori", illustratori)
            product = Product(
                name=titolo,
                id=id,
                barcode=isbn13,
                data_uscita=data_uscita,
                redazione=redazione,
                marchio_editoriale=marchio,
                book_type=tipo,
                in_magazzino=in_magazzino,
                # collana_id=None,
                collana_id=collana_id,
                autori_id=autori_id,
                curatori_id=curatori_id,
                prefatori_id=prefatori_id,
                traduttori_id=traduttori_id,
                illustratori_id=illustratori_id,
                data_cedola=data_cedola,
                nome_cedola=nome_cedola,
            )
            yield product

    def adjusted_fields(self, cls):
        fields = [f.name for f in attr.fields(cls)]
        logger.info("fields: %s", fields)
         
        return map(lambda x: x + "/id" if x.endswith("_id") else x, fields)

    def load_collane(self, infile):
        # import pdb; pdb.set_trace()
        fields = self.adjusted_fields(Collana)
        try:
            categorie_collane = self.get_collane(infile)
            for categoria in categorie_collane:
                values = [attr.astuple(categoria)]
                logger.info("Values: %s", values)
                results = self.env["stampa.collana"].load(fields, values)
                ids = self.set_ids_check_results(results)
                logger.info("ids: %s", ids)
        except:
            logger.exception("caricamento fallito")

    def load_products(self, infile):
        # import pdb; pdb.set_trace()
        count = 0
        fields = self.adjusted_fields(Product)
        logger.debug("Fields: %s", fields)
        try:
            products = self.get_products(infile)
            # partner_blocks = batch_generator(partners)
            for product in products:
                values = [attr.astuple(product)]
                logger.info("Values: %s", values)
                results = self.env["product.template"].load(fields, values)
                # logger.info("results: %s", results)
                ids = self.set_ids_check_results(results)
                # logger.debug("ids: %s", ids)
                count += len(ids)
            #logger.debug("Count: %s", count)
        except:
            logger.exception("caricamento fallito")

    def _create_sale_order(self, partner, titolo, row):

        # tag_name = u"Lancio del {}".format(row[31].strip())
        # tag_id = self.env['send.book']._get_order_tag(tag_name)
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

        so = False
        try:
            so = self.env["sale.order"].create(vals)
        except Exception as e:
            logger.exception(vals)

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
                self.env.cr.commit()
                logger.info(
                    "[{}] righe committate su database".format(countrow)
                )

            codice_critico = row[1]

            if codice_critico in self.DUPLICATED:
                logger.warning(
                    "Trovato critico vecchio [{}] da sostituire con [{}]".format(
                        codice_critico, self.DUPLICATED[codice_critico]
                    )
                )
                codice_critico = self.DUPLICATED[codice_critico]

            partner = self._get_partner_by_codice_critico(codice_critico)
            if not partner:
                logger.error(
                    "Partner con codice critico [{}] non trovato".format(
                        codice_critico
                    )
                )
                continue

            # cerco il titolo
            isbn = row[3]
            titolo = self._get_product_by_isbn(isbn)
            if not titolo:
                logger.error(
                    "Titolo non trovato con isbn [{}] non trovato".format(isbn)
                )
                continue

            so = self._create_sale_order(partner, titolo, row)
            if so:
                # logger.info('Ordine creato con Partner [{}]'.format(partner.name))
                # annullo la picking creata
                for picking in so.picking_ids:
                    picking.action_cancel()

        # logger.info("Import lanci")
        self.env.cr.commit()

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
        "71913": "94119",
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
        "92608": "102734",
        "58052": "91990",
        "77171": "101445",
        "94512": "103576",
        "74060": "94566",
        "78631": "98704",
        "94353": "103267",
        "77122": "100676",
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

    @environmentContextManager(manage_args_method="manage_args")
    def run(self, args, env):
        self.run_batch(args, env)

    def run_batch(self, args, env, fln_name=None):
        logger.info("Start")
         
        self.env = env
        with cursor(env):
            if args.categories:
                if args.collane:
                    with open(args.collane, "rb") as filename:
                        self.load_collane(filename)

            else:
                file_open = fln_name if fln_name else args.filename
                
                if file_open:
                    with open(file_open, "rb") as filename:
                        self.load_products(filename)

                if args.lanci:
                    logger.info("job import lanci: START")
                    start_time = time.time()

                    with open(args.lanci, "rb") as filename:
                        self._importa_lanci(filename)

                    logger.info(
                        "job import lanci: ENDED in %s seconds ---"
                        % (time.time() - start_time)
                    )

        logger.info("End")

class ImportProducts_14(ImportProducts):
    def run_batch(self, env, fln_name=None):
        #logger.info("Start ImportProducts_14")
         
        print("CIAOOOOOOOO")
        self.env = env
        with cursor(env):
            with open(fln_name, "rt", encoding="utf-8") as filename:
                self.load_products(filename)
        logger.info("End")
    def load_products(self, infile):
        self.get_products(infile)
    
    def get_products(self, infile):
        reader = self.utf_reader(infile)
        next(reader)  # skip first line
        # import pdb;pdb.set_trace()
        try:
            while True:
                line = next(reader)
                # id_gpe = line[0]
                isbn13 = line[1]
                titolo = line[2].strip()
                # sottotitolo = line[3].strip()
                collana_id = line[4].strip()
                collana = line[5].strip()
                data_uscita = line[6]
                in_magazzino = line[7]
                tipo = line[8].title()
                redazione = line[9]
                marchio = line[10].strip().title()
                autori = line[11]
                curatori = line[12]
                prefatori = line[13]
                traduttori = line[14]
                illustratori = line[15]
                nome_cedola = line[16]
                data_cedola = line[17]
                id = self.external_id("libri", isbn13)

                ##collana_id = collana_id
                collana_id = self.get_external_ids("collane", collana_id)
                autori_id = self.get_external_ids("autori", autori)
                curatori_id = self.get_external_ids("autori", curatori)
                prefatori_id = self.get_external_ids("autori", prefatori)
                traduttori_id = self.get_external_ids("autori", traduttori)
                illustratori_id = self.get_external_ids("autori", illustratori)
                product = Product(
                    name=titolo,
                    id=id,
                    barcode=isbn13,
                    data_uscita=data_uscita,
                    redazione=redazione,
                    marchio_editoriale=marchio,
                    book_type=tipo,
                    in_magazzino=in_magazzino,
                    # collana_id=None,
                    collana_id=collana_id,
                    autori_id=autori_id,
                    curatori_id=curatori_id,
                    prefatori_id=prefatori_id,
                    traduttori_id=traduttori_id,
                    illustratori_id=illustratori_id,
                    data_cedola=data_cedola,
                    nome_cedola=nome_cedola,
                )
                #yield product
                self.load_product(product)
        except StopIteration:
            print("FINE")
        except:
            print("ERRORE")
    
    def load_product(self, product):
        fields = self.adjusted_fields(Product)
        logger.debug("Fields: %s", fields)
        values = [attr.astuple(product)]
        logger.info("Values: %s", values)
         
        results = self.env["product.template"].load(fields, values)
        # logger.info("results: %s", results)
        ids = self.set_ids_check_results(results)
        #self.set_ids_check_results(results)
        logger.debug("ids: %s", ids)
        #count += len(ids)
        #logger.debug("Count: %s", count)

    def utf_reader(self, infile):
        reader = csv.reader(infile, delimiter=DELIMITER)
        while True:
            row = next(reader)
            yield [str(cell) for cell in row]
    def slugify(self,value):
        if not isinstance(value, str):
            value = value.decode(ENC, "ignore")
        value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore")
        value = re.sub("[^/\w\s@-]", "", value.decode('utf-8')).strip().lower()
        return re.sub("[-\s/]+", "_", value)
    def external_id(self,target, field):
        # import pdb; pdb.set_trace()
        key = self.slugify(field)
        ext_id = "feltricrm.%s_%s" % (target, key)
        return ext_id
    def get_external_ids(self, prefix, values):
        # import pdb; pdb.set_trace()
        #logger.debug("get_external_ids")
        categories = self.get_category_names(values)
        #logger.debug("categories: %s", categories)
        if not categories:
            return None
        cat_ids = [self.external_id(prefix, cat) for cat in categories]
        #logger.debug("cat_ids: %s", cat_ids)
        category_id = ",".join(cat_ids)
        #logger.debug("category_id: %s", category_id)
        return category_id