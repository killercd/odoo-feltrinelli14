from __future__ import print_function

import logging
import argparse
from itertools import islice, chain
import codecs
import csv
from datetime import datetime
import unicodedata
import re
from contextlib import contextmanager

import attr

from odoo.cli import Command
from odoo.addons.stampa.cli.run import environmentContextManager

logger = logging.getLogger(__name__)

BATCH = 10
DELIMITER = ";"
ENC = "utf-8"
RUOLI_COLOR = 4
ROLES_COLORS = {
    "AUTORE": 1,
    "CURATORE": 2,
    "PREFATORE": 4,
    "REGISTA": 5,
    "TRADUTTORE": 6,
    "ILLUSTRATORE": 7,
    "CONTRIBUTI": 8,
}


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
    logger.debug("infile %s", infile)
    reader = csv.reader(infile, delimiter=DELIMITER)
    logger.debug("reader %s", reader)
    for row in reader:
        logger.debug("row %s", row)
        yield [unicode(cell, "utf-8", "replace") for cell in row]


@attr.s
class Person(object):
    id = attr.ib()
    name = attr.ib()
    category_id = attr.ib(default=None)
    color = attr.ib(default=0)


@attr.s
class Partner(object):
    id = attr.ib()
    firstname = attr.ib()
    lastname = attr.ib(default=None)
    parent_id = attr.ib(default=None)
    email = attr.ib(default=None)
    phone = attr.ib(default=None)
    mobile = attr.ib(default=None)
    street = attr.ib(default=None)
    city = attr.ib(default=None)
    function = attr.ib(default=None)
    zip = attr.ib(default=None)
    state_id = attr.ib(default=None)
    country_id = attr.ib(default=None)
    fax = attr.ib(default=None)
    comment = attr.ib(default=None)
    website = attr.ib(default=None)
    category_id = attr.ib(default=None)
    is_company = attr.ib(default="false")


@attr.s
class Category(object):
    name = attr.ib()
    id = attr.ib()
    color = attr.ib(default=None)
    parent_id = attr.ib(default=None)


class ImportFromChimp(Command):
    def manage_args(self, args):
        parser = argparse.ArgumentParser()
        parser.add_argument("--debug", action="store_true")
        parser.add_argument("infile", type=argparse.FileType("r"))
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

    def get_partners(self, infile):
        reader = csv.reader(infile)
        reader.next()  # skip headers
        for line in reader:
            name = " ".join((line[1].decode(ENC), line[2].decode(ENC)))
            email = line[0].strip().lower()
            partner = Partner(
                firstname=name.title().strip(),
                email=email,
                id=external_id("contatti", email),
            )
            yield partner

    @environmentContextManager(manage_args_method="manage_args")
    def run(self, args, env):
        self.run_batch(args, env)

    def run_batch(self, args, env, fln_name=None):
        logger.info("Start")

        self.env = env
        count = 0
        fields = [f.name for f in attr.fields(Partner)]
        try:
            partners = self.get_partners(args.infile)
            partner_blocks = batch_generator(partners)
            for block in partner_blocks:
                values = [attr.astuple(p) for p in block]
                results = env["res.partner"].load(fields, values)
                ids = self.set_ids_check_results(results)
                count += len(ids)
                logger.info("So far: %s", count)
        except Exception:
            logger.exception("caricamento fallito")
        finally:
            self.teardown()

    def teardown(self):
        self.env.cr.close()
        logger.info("End")


ADDRESSES_KIND = [u"ufficio", u"abitazione", u"altro"]
ADDRESSES_MAPPING = {
    ADDRESSES_KIND[0]: {
        "via": 8,
        "citta": 11,
        "provincia": 12,
        "cap": 13,
        "stato": 14,
        "fax": 30,
        "telefono": 31,
        "cellulare": 32,
        "email": 71,
    },
    ADDRESSES_KIND[1]: {
        "via": 15,
        "citta": 18,
        "provincia": 19,
        "cap": 20,
        "stato": 21,
        "fax": 36,
        "telefono": 37,
        "cellulare": 38,
        "email": 74,
    },
    ADDRESSES_KIND[2]: {
        "via": 22,
        "citta": 25,
        "provincia": 26,
        "cap": 27,
        "stato": 28,
        "fax": 41,
        "telefono": 42,
        "cellulare": 40,
        "email": 77,
    },
}


class ImportFromOutlook(Command):
    _cache_state_ids = {}
    _cache_country_ids = {}

    env = None

    state_model = None
    country_model = None

    country_italy = None

    def _correct_line(self, line):
        # import pdb;pdb.set_trace()
        corrected_line = []

        for value in line:
            value = value.decode(ENC)
            if value:
                value = value.strip()

            corrected_line.append(value)

        return corrected_line

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
        names = field.split(";")
        names = map(lambda x: x.strip().title(), names)
        return filter(None, names)

    def get_categories(self, infile):
        reader = csv.reader(infile, delimiter=DELIMITER)
        reader.next()
        found = set()

        for line in reader:
            line = self._correct_line(line)
            names = self.get_category_names(line[51])

            for name in names:
                found.add(name)

        return [
            Category(name=name, id=external_id("categorie", name))
            for name in found
        ]

    def load_categories(self, infile):
        categorie = self.get_categories(infile)
        logger.debug("categorie: %s", categorie)
        fields = self.adjusted_fields(Category)
        values = [attr.astuple(c) for c in categorie]
        results = self.env["res.partner.category"].load(fields, values)
        ids = self.set_ids_check_results(results)
        logger.debug("ids: %s", ids)

    def _search_one(self, model, domain):
        results = model.search(domain)

        if results:
            try:
                results.ensure_one()

                return results

            except ValueError:
                return None

        else:
            return None

    def _get_country_id(self, name):
        country_id = None

        if name:
            if name in self._cache_country_ids:
                country_id = self._cache_country_ids[name]

            else:
                country_id = self._search_one(
                    self.country_model, [("name", "ilike", name)]
                )

                self._cache_country_ids[name] = country_id

        return country_id

    def _get_state_id(self, name, country_id=None):
        state_id = None

        if name:
            if name in self._cache_state_ids:
                state_id = self._cache_state_ids[name]

            else:
                # Cerco solo le province dello stato trovato precedentemente...
                #
                if country_id:
                    state_id = self._search_one(
                        self.state_model,
                        [
                            ("name", "ilike", name),
                            ("country_id", "=", country_id.id),
                        ],
                    )

                    if not state_id:
                        state_id = self._search_one(
                            self.state_model,
                            [
                                ("code", "ilike", name),
                                ("country_id", "=", country_id.id),
                            ],
                        )

                # Cerco tutte le province corrispondenti per nome e codice...
                #
                if not state_id:
                    state_id = self._search_one(
                        self.state_model, [("name", "ilike", name)]
                    )

                    if not state_id:
                        state_id = self._search_one(
                            self.state_model, [("code", "ilike", name)]
                        )

                # Cerco (se non ho trovato corrispondenze precedentemente) solo le province italiane...
                #
                if not state_id:
                    state_id = self._search_one(
                        self.state_model,
                        [
                            ("name", "ilike", name),
                            ("country_id", "=", self.country_italy.id),
                        ],
                    )

                    if not state_id:
                        state_id = self._search_one(
                            self.state_model,
                            [
                                ("code", "ilike", name),
                                ("country_id", "=", self.country_italy.id),
                            ],
                        )

                self._cache_state_ids[name] = state_id

        return state_id

    def _get_contact(self, line, kind):
        # import pdb;pdb.set_trace()
        if kind not in ("ufficio", "abitazione", "altro"):
            raise NotImplementedError()

        contact = {}
        mapping = ADDRESSES_MAPPING[kind]

        for key, index in mapping.items():
            value = line[index]

            if value and value != "":
                contact[key] = value

        return contact

    def _get_contacts(self, line):
        # import pdb;pdb.set_trace()
        contacts = []

        for kind in ADDRESSES_KIND:
            contact = self._get_contact(line, kind)

            if contact:
                contact["kind"] = kind
                contacts.append(contact)

        return contacts

    def get_partners(self, infile):
        # import pdb;pdb.set_trace()
        reader = csv.reader(infile, delimiter=DELIMITER)
        reader.next()  # skip first line

        for line in reader:
            line = self._correct_line(line)

            societa = line[5]
            if societa:
                company_id = external_id("contatti", societa)
                company = Partner(
                    id=company_id, firstname=societa, is_company="true"
                )

                yield company

            names = []

            firstname = line[1]
            if firstname and firstname != "":
                names.append(firstname)

            secondname = line[2]
            if secondname and secondname != "":
                names.append(secondname)

            lastname = line[3]
            if lastname and lastname != "":
                names.append(lastname)

            name = u" ".join(names)
            if not name:
                continue

            firstname = u"{} {}".format(firstname, secondname).strip()

            contacts = self._get_contacts(line)
            if not contacts:
                continue

            main_contact = contacts[0]

            email = main_contact.get("email")
            phone = main_contact.get("telefono")
            mobile = main_contact.get("cellulare")

            if phone:
                name += phone

            elif mobile:
                name += mobile

            partner_id = email or name
            partner_id = external_id("contatti", partner_id)

            function = line[7]

            street = main_contact.get("via")
            city = main_contact.get("citta")
            zip_code = main_contact.get("cap")
            fax = main_contact.get("fax")

            note = u"{}\n".format(line[67])
            website = line[69]
            parent_id = company_id if societa else None

            category_id = None
            categories = self.get_category_names(line[51])
            if categories:
                cat_ids = [external_id("categorie", cat) for cat in categories]
                category_id = ",".join(cat_ids)

            country_name = main_contact.get("stato")
            state_name = main_contact.get("provincia")

            country_id = self._get_country_id(country_name)
            state_id = self._get_state_id(state_name, country_id=country_id)

            if state_id:
                if not country_id and country_name:
                    self._cache_country_ids[country_name] = state_id.country_id

                country_id = str(state_id.country_id.id)
                state_id = str(state_id.id)

            else:
                if country_id:
                    country_id = str(country_id.id)

                elif country_name:
                    note += "Stato: '%s'\n" % country_name

                if state_name:
                    note += "Provincia: '%s'\n" % state_name

            partner = Partner(
                firstname=firstname,
                lastname=lastname,
                email=email,
                phone=phone,
                mobile=mobile,
                id=partner_id,
                street=street,
                city=city,
                function=function,
                zip=zip_code,
                fax=fax,
                comment=note,
                website=website,
                parent_id=parent_id,
                category_id=category_id,
                country_id=country_id,
                state_id=state_id,
            )

            yield partner

            for index, contact in enumerate(contacts):
                if index == 0:
                    continue

                note = u""

                address_id = external_id(
                    "contatti", "{}_{}".format(partner_id, contact["kind"])
                )

                country_name = contact.get("stato")
                state_name = contact.get("provincia")

                country_id = self._get_country_id(country_name)
                state_id = self._get_state_id(
                    state_name, country_id=country_id
                )

                if state_id:
                    if not country_id and country_name:
                        self._cache_country_ids[
                            country_name
                        ] = state_id.country_id

                    country_id = str(state_id.country_id.id)
                    state_id = str(state_id.id)

                else:
                    if country_id:
                        country_id = str(country_id.id)

                    elif country_name:
                        note += u"Stato: '%s'\n" % country_name

                    if state_name:
                        note += u"Provincia: '%s'\n" % state_name

                address_kind = contact["kind"].title()

                address = Partner(
                    id=address_id,
                    parent_id=partner_id,
                    firstname="%s (%s)" % (firstname, address_kind),
                    lastname=lastname,
                    street=contact.get("via"),
                    city=contact.get("citta"),
                    zip=contact.get("cap"),
                    phone=contact.get("telefono"),
                    mobile=contact.get("cellulare"),
                    fax=contact.get("fax"),
                    email=contact.get("email"),
                    country_id=country_id,
                    state_id=state_id,
                    comment=note,
                    type="other",
                )

                yield address

    def adjusted_fields(self, cls):
        fields = [f.name for f in attr.fields(cls)]

        fields = map(lambda x: x + "/id" if x.endswith("_id") else x, fields)
        return map(
            lambda x: x.replace("_xid", "_id") + "/.id"
            if x.endswith("_xid")
            else x,
            fields,
        )

    def create_relations(self, ids):
        from odoo.addons.partner_contact_employees.cli.make_employees import (
            MakeEmployees,
        )

        Relation = self.env["res.partner.relation"].with_context(
            mail_create_nosubscribe=True
        )
        ResPartnerRelationEmployee = self.env[
            "res.partner.relation.employee"
        ].with_context(mail_create_nosubscribe=True)

        employee_of = self.env.ref(
            "partner_contact_relations.relation_type_employee_of"
        ).id
        for partner in self.env["res.partner"].browse(ids):
            if partner.parent_id:
                rel = Relation.create(
                    {
                        "src_partner_id": partner.id,
                        "type_id": employee_of,
                        "dest_partner_id": partner.parent_id.id,
                    }
                )
                ResPartnerRelationEmployee.create(
                    MakeEmployees.compute_vals(rel)
                )

    def load_partners(self, infile):
        # import pdb;pdb.set_trace()
        count = 0
        fields = self.adjusted_fields(Partner)
        logger.debug("Fields: %s", fields)
        try:
            partners = self.get_partners(infile)
            # partner_blocks = batch_generator(partners)

            for partner in partners:
                logger.debug("Partner letti %s", partner)
                values = [attr.astuple(partner)]
                logger.debug("Values: %s", values)
                results = self.env["res.partner"].load(fields, values)
                ids = self.set_ids_check_results(results)
                # self.create_relations(ids)
                logger.debug("ids: %s", ids)
                count += len(ids)
        except Exception:
            logger.exception("caricamento fallito")

    def manage_args(self, args):
        parser = argparse.ArgumentParser()
        parser.add_argument("--debug", action="store_true")
        parser.add_argument("--categories", action="store_true")
        # parser.add_argument('infile', type=argparse.FileType('r'))
        parser.add_argument("--filename")
        args, unknown = parser.parse_known_args(args)

        return args, unknown

    @environmentContextManager(manage_args_method="manage_args")
    def run(self, args, env):
        # import pdb;pdb.set_trace()
        logger.info("Start")

        self.env = env

        with cursor(env):
            self.state_model = self.env["res.country.state"]
            self.country_model = self.env["res.country"]
            self.country_italy = self.env.ref("base.it")

            if args.categories:
                self.load_categories(args.infile)

            else:
                # self.load_partners(args.infile)
                if args.filename:
                    with open(args.filename, "rb") as filename:
                        self.load_partners(filename)

        logger.info("End")


class ImportAuthors(ImportFromOutlook):
    def adjusted_categories_fields(self, cls):
        return super(ImportAuthors, self).adjusted_fields(cls)

    def adjusted_authors_fields(self, cls):
        fields = super(ImportAuthors, self).adjusted_fields(cls)
        return filter(lambda x: x != "color", fields)

    def get_category_ruoli(self):
        return Category(name="Ruoli", id=external_id("categorie", "ruoli"))

    def get_categories(self, infile):
        #import pdb;pdb.set_trace()
        reader = utf_reader(infile)
        reader.next()

        found = set()
        ruoli = self.get_category_ruoli()

        for line in reader:
            names = self.get_category_names(line[3])
            for name in names:
                found.add(name)

        ruoli_parent = Category(
            name="Ruoli", id=external_id("categorie", "ruoli")
        )

        ruoli = [
            Category(
                name=name,
                id=external_id("ruoli", name),
                parent_id=ruoli.id,
                color=RUOLI_COLOR,
            )
            for name in found
        ]

        return [ruoli_parent] + ruoli

    def load_categories(self, infile):
        # import pdb;pdb.set_trace()
        categorie = self.get_categories(infile)
        logger.info("Categorie: %s", categorie)

        fields = self.adjusted_categories_fields(Category)
        logger.debug("Fields: %s", fields)

        values = [attr.astuple(c) for c in categorie]
        results = self.env["stampa.person.category"].load(fields, values)

        ids = self.set_ids_check_results(results)
        logger.debug("Ids: %s", ids)

    def get_people(self, infile):
        # import pdb;pdb.set_trace()
        reader = utf_reader(infile)
        # reader.next()  # Skip first line...

        for line in reader:
            if len(line) != 4:
                logger.exception("Lunghezza riga errata %s", line)
                raise
            id_gpe = line[0]
            if not id_gpe.isdigit():
                continue
            cognome = line[1]
            nome = line[2]
            ruoli = line[3]

            name = " ".join([nome, cognome]).strip()
            if not name:
                continue

            id_person = external_id("autori", id_gpe)

            category_id = None
            categories = self.get_category_names(ruoli)

            if categories:
                if categories[0].upper() not in ROLES_COLORS:
                    continue
                color = ROLES_COLORS[categories[0].upper()]

                cat_ids = [external_id("ruoli", cat) for cat in categories]
                category_id = ",".join(cat_ids)

            person = Person(
                id=id_person, name=name, category_id=category_id, color=color
            )

            yield person

    def load_partners(self, infile):
        # import pdb;pdb.set_trace()
        count = 0
        fields = self.adjusted_authors_fields(Person)
        logger.debug("Fields: %s", fields)

        try:
            people = self.get_people(infile)

            for person in people:
                logger.info("Person: %s", person)

                values = [attr.astuple(person)]

                fields.append("color")
                results = self.env["stampa.person"].load(fields, values)
                ids = self.set_ids_check_results(results)

                logger.debug("Ids: %s", ids)

                count += len(ids)

        except Exception:
            logger.exception("Caricamento fallito!")


class ImportFromInfolib(Command):
    _cache_state_ids = {}
    _cache_country_name_ids = {}
    _cache_country_code_ids = {}
    _cache_orders_ids = {}
    _cache_orders_tags_ids = {}

    is_debugging = False

    env = None

    state_model = None
    country_model = None

    country_italy = None

    partner_mapping = (
        (0, "_compute_external_id"),
        (1, "_compute_lastname"),
        (3, "_compute_firstname"),
        (5, "_compute_company_type"),
        (6, "street"),
        (8, "city"),
        (9, "zip"),
        (10, "_compute_state_id"),
        (12, "_compute_country_code"),
        (13, "_compute_country_name"),
        (14, "street2"),
        (15, "_compute_birth_date"),  # YYYY-MM-DD HH:MM:SS.SSS
        (17, "phone"),
        (18, "fax"),
        (19, "email"),
        (20, "_compute_email_2"),
        (21, "_compute_email_3"),
        (22, "website"),
        (23, "_compute_vat"),
        (24, "_compute_fiscal_code"),
        (25, "_compute_active"),
    )

    address_mapping = (
        (0, "_compute_partner_id"),
        (1, "lastname"),
        (2, "_compute_firstname"),
        (3, "street"),
        (4, "zip"),
        (5, "city"),
        (6, "_compute_state_id"),
        (8, "_compute_country_code"),
        (9, "_compute_country_name"),
        (11, "_compute_building"),
        (12, "phone"),
        (13, "_compute_fax"),
        (14, "street2"),
    )

    tag_mapping = ((0, "_compute_partner_id"), (2, "_compute_tags"))

    order_mapping = (
        (0, "_compute_product_id"),
        (2, "_compute_tag_ids"),
        (3, "product_uom_qty"),
        (4, "date_order"),
        (5, "_compute_partner_id"),
    )

    def _compose_external_id(self, model, field, module=None):
        if not module:
            module = "infolib"

        return "%s.%s_%s" % (module, model, slugify(field))

    def _compose_partner_external_id(self, id):
        return self._compose_external_id("contatti", id)

    def _compose_partner_tag_external_id(self, index, name):
        return self._compose_external_id(
            "classificazioni", "%s_%s" % (index, name)
        )

    def _compose_order_external_id(self, partner_code, order_date):
        return self._compose_external_id(
            "ordini", "%s_%s" % (partner_code, order_date)
        )

    def _compose_order_line_external_id(self, isbn, partner_code, order_date):
        return self._compose_external_id(
            "righe_ordini", "%s_%s_%s" % (isbn, partner_code, order_date)
        )

    def _compose_order_tag_external_id(self, tag_name):
        return self._compose_external_id("tags_ordini", tag_name)

    def _compose_product_external_id(self, isbn):
        return self._compose_external_id("libri", isbn, module="feltricrm")

    def _get_entity(self, line, mapping):
        try:
            entity = {}

            for index, key in mapping:
                value = line[index].decode(ENC)

                if not value:
                    continue

                value = value.strip()

                if value == "" or value == "NULL":
                    continue

                entity[key] = value

            return entity

        except IndexError:
            print("")
            logger.exception(
                "Some columns on this line seems missing! Maybe it's a parsing problem? "
                "(Delimiter is '%s')" % DELIMITER
            )
            print("")
            print(line)
            print("")

            if self.is_debugging:
                raise

    def _search_by_external_id(self, external_id):
        parts = external_id.split(".")

        base = parts[0]
        external_id = parts[1]

        try:
            res_model, res_id = self.env["ir.model.data"].get_object_reference(
                base, external_id
            )

            return self.env[res_model].browse(res_id)

        except ValueError:
            return None

    def _search_one(self, model, domain):
        results = model.search(domain)

        if results:
            try:
                results.ensure_one()

                return results

            except ValueError:
                return None

        else:
            return None

    def _get_country_id(self, name, code):
        country_id = None

        if name and name in self._cache_country_name_ids:
            country_id = self._cache_country_name_ids[name]

        elif code and code in self._cache_country_code_ids:
            country_id = self._cache_country_code_ids[code]

        else:
            if name:
                country_id = self._search_one(
                    self.country_model, [("name", "ilike", name)]
                )

            if not country_id and code:
                country_id = self._search_one(
                    self.country_model, [("code", "ilike", code)]
                )

            if name:
                self._cache_country_name_ids[name] = country_id
            if code:
                self._cache_country_code_ids[code] = country_id

        return country_id

    def _get_state_id(self, name, country_id=None):
        state_id = None

        if name:
            if name in self._cache_state_ids:
                state_id = self._cache_state_ids[name]

            else:
                # Cerco solo le province dello stato trovato precedentemente...
                #
                if country_id:
                    state_id = self._search_one(
                        self.state_model,
                        [
                            ("name", "ilike", name),
                            ("country_id", "=", country_id.id),
                        ],
                    )

                    if not state_id:
                        state_id = self._search_one(
                            self.state_model,
                            [
                                ("code", "ilike", name),
                                ("country_id", "=", country_id.id),
                            ],
                        )

                # Cerco tutte le province corrispondenti per nome e codice...
                #
                if not state_id:
                    state_id = self._search_one(
                        self.state_model, [("name", "ilike", name)]
                    )

                    if not state_id:
                        state_id = self._search_one(
                            self.state_model, [("code", "ilike", name)]
                        )

                # Cerco (se non ho trovato corrispondenze precedentemente) solo le province italiane...
                #
                if not state_id:
                    state_id = self._search_one(
                        self.state_model,
                        [
                            ("name", "ilike", name),
                            ("country_id", "=", self.country_italy.id),
                        ],
                    )

                    if not state_id:
                        state_id = self._search_one(
                            self.state_model,
                            [
                                ("code", "ilike", name),
                                ("country_id", "=", self.country_italy.id),
                            ],
                        )

                self._cache_state_ids[name] = state_id

        return state_id

    def _get_partner(self, line):
        note = ""
        partner = self._get_entity(line, self.partner_mapping)

        # External ID
        #
        partner["id"] = self._compose_partner_external_id(
            partner["_compute_external_id"]
        )

        # Persona fisica / Persona giuridica...
        #
        if partner.get("_compute_company_type", "0") == "1":
            partner["company_type"] = "person"

            if "_compute_lastname" in partner:
                names = partner["_compute_lastname"].split(" ", 1)

                if len(names) > 0:
                    partner["lastname"] = names[0]
                else:
                    partner["lastname"] = ""

                if len(names) > 1:
                    partner["firstname"] = names[1]
                else:
                    partner["firstname"] = ""

            else:
                partner["invalid"] = True

                return partner

        else:
            partner["company_type"] = "company"
            partner["name"] = (
                "%s %s"
                % (
                    partner.get("_compute_lastname", ""),
                    partner.get("_compute_firstname", ""),
                )
            ).strip()

        # Data di nascita...
        #
        if "_compute_birth_date" in partner:
            birth_date = partner["_compute_birth_date"].split(" ", 1)
            birth_date = datetime.strptime(birth_date[0], "%Y-%m-%d")
            birth_date = birth_date.strftime("%d/%m/%Y")

            note += "Data di nascita: '%s'\n" % birth_date

        # Stato e provincia...
        #
        state_name = partner.get("_compute_state_id")
        country_name = partner.get("_compute_country_name")
        country_code = partner.get("_compute_country_code")

        country_id = self._get_country_id(country_name, country_code)
        state_id = self._get_state_id(state_name, country_id=country_id)

        if state_id:
            partner["state_id/.id"] = "%d" % state_id.id
            partner["country_id/.id"] = "%d" % state_id.country_id.id

            if not country_id:
                if country_name:
                    self._cache_country_name_ids[
                        country_name
                    ] = state_id.country_id
                if country_code:
                    self._cache_country_code_ids[
                        country_code
                    ] = state_id.country_id

        else:
            if country_id:
                partner["country_id/.id"] = "%d" % country_id.id

            else:
                country = None

                if country_name:
                    country = "%s" % country_name

                    if country_code:
                        country += " (%s)" % country_code

                elif country_code:
                    country = "%s" % country_code

                if country:
                    note += "Stato: '%s'\n" % country

            if state_name:
                note += "Provincia: '%s'\n" % state_name

        if country_id and country_id.id != self.country_italy.id:
            logger.warning(
                "Partner with external ID '%s' is not Italian!" % partner["id"]
            )

        # e-mail 2 & e-mail 3...
        #
        if "_compute_email_2" in partner:
            note += "E-mail 2: '%s'" % partner["_compute_email_2"]

        if "_compute_email_3" in partner:
            note += "E-mail 3: '%s'" % partner["_compute_email_3"]

        # Partita Iva e Codice fiscale...
        #
        vat = partner.get("_compute_vat")
        fiscal_code = partner.get("_compute_fiscal_code")

        if vat:
            note += "Partita IVA: '%s'\n" % vat

        if fiscal_code:
            note += "Codice fiscale: '%s'\n" % fiscal_code

        # Attivo / Disattivo..
        #
        active = partner.get("_compute_active", "1")
        partner["active"] = "%s" % (active == "1")

        # Note...
        #
        note = note.strip()

        if note != "":
            partner["comment"] = note

        # Rimuovo da partner le chiavi dei campi calcolati...
        #
        partner.pop("_compute_external_id")
        partner.pop("_compute_company_type")
        partner.pop("_compute_lastname", None)
        partner.pop("_compute_firstname", None)
        partner.pop("_compute_birth_date")
        partner.pop("_compute_state_id", None)
        partner.pop("_compute_country_name", None)
        partner.pop("_compute_country_code", None)
        partner.pop("_compute_email_2", None)
        partner.pop("_compute_email_3", None)
        partner.pop("_compute_vat", None)
        partner.pop("_compute_fiscal_code", None)
        partner.pop("_compute_active", None)

        return partner

    def _get_partners(self, reader):
        for line in reader:
            yield self._get_partner(line)

    def _import_partners(self, filename):
        logger.info("Now starting importing partners...")

        reader = csv.reader(filename, delimiter=DELIMITER)
        reader.next()  # Skip first line...

        partners = self._get_partners(reader)

        for partner in partners:
            if "invalid" in partner:
                logger.error(
                    "Partner with external ID '%s' seems invalid!"
                    % partner["id"]
                )
                continue

            fields = partner.keys()
            values = [partner.values()]
            result = self.env["res.partner"].load(fields, values)

            if result["messages"]:
                logger.error(
                    "Unable to properly import partner with external ID '%s' due of:"
                    % partner["id"]
                )
                for message in result["messages"]:
                    print(" -> %s" % message["message"])

                print("")
                print(fields)
                print(values)
                print("")

                self.rollback()

                if self.is_debugging:
                    return

            elif result["ids"]:
                logger.debug("Imported partner with ID: '%s'" % result["ids"])

                self.commit()

            else:
                self.rollback()

                raise Exception(
                    "I don't know why this is happening, but it's happening anyway!"
                )

        logger.info("All partners has just been correctly imported!")

    def _get_address(self, line):
        note = ""
        address = self._get_entity(line, self.address_mapping)

        # Campi valorizzati così, in ogni caso...
        #
        address["type"] = "other"
        address["debit_limit"] = "0"
        address["credit_limit"] = "0"

        # Partner external ID...
        #
        address["parent_id/id"] = self._compose_partner_external_id(
            address["_compute_partner_id"]
        )
        address["commercial_partner_id/id"] = address["parent_id/id"]

        # Racchiudo tra parentesi il tipo di indirizzo e lo salvo nel "firstname"...
        #
        address["firstname"] = "(%s)" % address["_compute_firstname"]

        # Stato e provincia...
        #
        state_name = address.get("_compute_state_id")
        country_name = address.get("_compute_country_name")
        country_code = address.get("_compute_country_code")

        country_id = self._get_country_id(country_name, country_code)
        state_id = self._get_state_id(state_name, country_id=country_id)

        if state_id:
            address["state_id/.id"] = "%d" % state_id.id
            address["country_id/.id"] = "%d" % state_id.country_id.id

            if not country_id:
                if country_name:
                    self._cache_country_name_ids[
                        country_name
                    ] = state_id.country_id
                if country_code:
                    self._cache_country_code_ids[
                        country_code
                    ] = state_id.country_id

        else:
            if country_id:
                address["country_id/.id"] = "%d" % country_id.id

            else:
                country = None

                if country_name:
                    country = "%s" % country_name

                    if country_code:
                        country += " (%s)" % country_code

                elif country_code:
                    country = "%s" % country_code

                if country:
                    note += "Stato: '%s'\n" % country

            if state_name:
                note += "Provincia: '%s'\n" % state_name

        if country_id and country_id.id != self.country_italy.id:
            logger.warning(
                "Address for partner with ID '%s' is not Italian!"
                % address["parent_id/id"]
            )

        # Building...
        #
        if "_compute_building" in address:
            note += "Edificio: '%s'\n" % address["_compute_building"]

        # Fax...
        #
        if "_compute_fax" in address:
            note += "Fax: '%s'\n" % address["_compute_fax"]

        # Note...
        #
        note = note.strip()

        if note != "":
            address["comment"] = note

        # Rimuovo da address le chiavi dei campi calcolati...
        #
        address.pop("_compute_partner_id")
        address.pop("_compute_firstname")
        address.pop("_compute_state_id", None)
        address.pop("_compute_country_name", None)
        address.pop("_compute_country_code", None)
        address.pop("_compute_building", None)
        address.pop("_compute_fax", None)

        return address

    def _get_addresses(self, reader):
        for line in reader:
            yield self._get_address(line)

    def _import_addresses(self, filename):
        logger.info("Now starting importing addresses...")

        reader = csv.reader(filename, delimiter=DELIMITER)
        reader.next()  # Skip first line...

        addresses = self._get_addresses(reader)

        for address in addresses:
            fields = address.keys()
            values = [address.values()]

            result = self.env["res.partner"].load(fields, values)

            if result["messages"]:
                logger.error(
                    "Unable to properly import address for partner with external ID '%s' due of:"
                    % address["parent_id/id"]
                )
                for message in result["messages"]:
                    print(" -> %s" % message["message"])

                print("")
                print(fields)
                print(values)
                print("")

                self.rollback()

                if self.is_debugging:
                    return

            elif result["ids"]:
                logger.debug(
                    "Imported address for partner with external ID '%s': '%s'"
                    % (address["parent_id/id"], result["ids"])
                )

                self.commit()

            else:
                self.rollback()

                raise Exception(
                    "I don't know why this is happening, but it's happening anyway!"
                )

        logger.info("All addresses has just been correctly imported!")

    def _get_partners_tags_lines(self, reader):
        for line in reader:
            yield self._get_entity(line, self.tag_mapping)

    def _get_partners_tags(self, reader, get_partner_id=False):
        lines = self._get_partners_tags_lines(reader)

        for line in lines:
            tag_id = None

            hierarchy = line["_compute_tags"].split("\\")
            hierarchy_length = len(hierarchy)

            for index, name in enumerate(hierarchy):
                tag = {"name": name.strip()}

                if tag_id:
                    tag["parent_id/id"] = tag_id

                tag_id = self._compose_partner_tag_external_id(
                    index, tag["name"]
                )
                tag["id"] = tag_id

                if get_partner_id and index == (hierarchy_length - 1):
                    tag[
                        "_compute_partner_id"
                    ] = self._compose_partner_external_id(
                        line["_compute_partner_id"]
                    )

                yield tag

    def _import_partners_tags(self, filename):
        logger.info("Now starting importing partners' tags...")

        reader = csv.reader(filename, delimiter=DELIMITER)
        reader.next()  # Skip first line...

        tags = self._get_partners_tags(reader)

        for tag in tags:
            fields = tag.keys()
            values = [tag.values()]

            result = self.env["res.partner.category"].load(fields, values)

            if result["messages"]:
                print("")
                logger.error(
                    "Unable to properly import category with external ID '%s' due of:"
                    % tag["id"]
                )
                for message in result["messages"]:
                    print(" -> %s" % message["message"])

                print("")
                print(fields)
                print(values)
                print("")

                self.rollback()

                if self.is_debugging:
                    return

            elif result["ids"]:
                logger.debug("Imported category with ID: '%s'" % result["ids"])

                self.commit()

            else:
                self.rollback()

                raise Exception(
                    "I don't know why this is happening, but it's happening anyway!"
                )

        logger.info("All partners' tags has just been correctly imported!")

    def _get_partners_tags_associations(self, reader):
        associations = {}
        lines = self._get_partners_tags(reader, get_partner_id=True)

        for line in lines:
            if "_compute_partner_id" in line:
                partner_id = line["_compute_partner_id"]

                if partner_id not in associations:
                    associations[partner_id] = []

                associations[partner_id].append(line["id"])

        return associations

    def _create_partners_tags_associations(self, filename):
        logger.info(
            "Now starting creating tags associations between partner..."
        )
        # import pdb; pdb.set_trace()
        reader = csv.reader(filename, delimiter=DELIMITER)
        reader.next()  # Skip first line...

        # codice_critico = 0
        # for line in reader:
        #     codice_critico = line[0]

        associations = self._get_partners_tags_associations(reader)

        for partner_id, category_ids in associations.items():
            fields = ["id", "category_id/id"]

            codice_critico = partner_id.replace("infolib.contatti_", "")
            # partner = self.env['res.partner'].search([('codice_critico','=',codice_critico)])
            external_id = "feltricontact_" + str(codice_critico)

            # partner_id = str(codice_critico)
            values = [[external_id, ",".join(category_ids)]]

            result = self.env["res.partner"].load(fields, values)

            if result["messages"]:
                print("")
                logger.error(
                    "Unable to create new tags associations between partner with external ID '%s' due of:"
                    % partner_id
                )
                for message in result["messages"]:
                    print(" -> %s" % message["message"])

                print("")
                print(fields)
                print(values)
                print("")

                self.rollback()

                if self.is_debugging:
                    return

            elif result["ids"]:
                logger.debug(
                    "Created new tags associations between partner with external ID '%s' "
                    % partner_id
                )

                self.commit()

            else:
                self.rollback()

                raise Exception(
                    "I don't know why this is happening, but it's happening anyway!"
                )

        logger.info(
            "All tags associations between partners has just been correctly created!"
        )

    def _get_order_line(self, line):
        order_line = self._get_entity(line, self.order_mapping)

        # External ID
        #
        order_line["id"] = self._compose_order_line_external_id(
            order_line["_compute_product_id"],
            order_line["_compute_partner_id"],
            order_line["date_order"],
        )

        # Order line fields
        #
        order_line["price_unit"] = "0.0"

        # Order external ID
        #
        order_line["_compute_order_id"] = self._compose_order_external_id(
            order_line["_compute_partner_id"], order_line["date_order"]
        )

        # Partner external ID
        #
        order_line["partner_id/id"] = self._compose_partner_external_id(
            order_line["_compute_partner_id"]
        )

        # Product external ID
        #
        order_line["product_id/id"] = self._compose_product_external_id(
            order_line["_compute_product_id"]
        )

        # Product UOM ID
        #
        order_line["product_uom/.id"] = "1"

        # Rimuovo da order_line le chiavi dei campi calcolati...
        #
        order_line.pop("_compute_tag_ids")
        order_line.pop("_compute_partner_id")
        order_line.pop("_compute_product_id")

        return order_line

    def _get_orders_lines(self, reader):
        for line in reader:
            yield self._get_order_line(line)

    def _get_order_id(self, order):
        order_id = self._search_by_external_id(order["id"])

        # Se non esiste ancora l'order, lo creo...
        #
        if not order_id:
            fields = order.keys()
            values = [order.values()]

            result = self.env["sale.order"].load(fields, values)

            if result["messages"]:
                print("")
                logger.error(
                    "Unable to properly import order with external ID '%s' due of:"
                    % order["id"]
                )
                for message in result["messages"]:
                    print(" -> %s" % message["message"])

                print("")
                print(fields)
                print(values)
                print("")

                self.rollback()

                if self.is_debugging:
                    return

            elif result["ids"]:
                logger.debug(
                    "Imported order with external ID '%s': '%s'"
                    % (order["id"], result["ids"])
                )

                self.commit()

                order_id = "%s" % result["ids"][0]

            else:
                self.rollback()

                raise Exception(
                    "I don't know why this is happening, but it's happening anyway!"
                )

        else:
            order_id = "%s" % order_id.id

        return order_id

    def _import_orders_lines(self, filename):
        print("")
        logger.info("Now starting importing orders lines...")

        reader = csv.reader(filename, delimiter=DELIMITER)
        reader.next()  # Skip first line...

        orders_lines = self._get_orders_lines(reader)

        for order_line in orders_lines:
            # Recupero l'order associato alla order_line corrente...
            #
            order_external_id = order_line["_compute_order_id"]

            if order_external_id not in self._cache_orders_ids:
                order_id = self._get_order_id(
                    {
                        "id": order_external_id,
                        "date_order": order_line["date_order"],
                        "partner_id/id": order_line["partner_id/id"],
                    }
                )

                self._cache_orders_ids[order_external_id] = order_id

            order_line["order_id/.id"] = self._cache_orders_ids[
                order_external_id
            ]

            # Rimuovo da order_line le chiavi dei campi appartenenti ad order...
            #
            order_line.pop("_compute_order_id")
            order_line.pop("date_order")
            order_line.pop("partner_id/id")

            fields = order_line.keys()
            values = [order_line.values()]
            result = self.env["sale.order.line"].load(fields, values)

            if result["messages"]:
                print("")
                logger.error(
                    "Unable to properly import sale order line with external ID '%s' due of:"
                    % order_line["id"]
                )
                for message in result["messages"]:
                    print(" -> %s" % message["message"])

                print("")
                print(fields)
                print(values)
                print("")

                self.rollback()

                if self.is_debugging:
                    return

            elif result["ids"]:
                logger.debug(
                    "Imported sale order line with external ID '%s': '%s'"
                    % (order_line["id"], result["ids"])
                )

                self.commit()

            else:
                self.rollback()

                raise Exception(
                    "I don't know why this is happening, but it's happening anyway!"
                )

        logger.info("All sale orders lines has just been correctly imported!")

    def _get_order_tag(self, line):
        tag = self._get_entity(line, self.order_mapping)

        # Order external ID
        #
        tag["id"] = self._compose_order_external_id(
            tag["_compute_partner_id"], tag["date_order"]
        )

        tag_name = tag["_compute_tag_ids"].split("\\")[1]

        # Tag external ID
        #
        tag["_compute_tag_ids"] = self._compose_order_tag_external_id(tag_name)

        # Tag fields...
        #
        tag["name"] = tag_name

        # Rimuovo da tag le chiavi dei campi calcolati...
        #
        tag.pop("_compute_product_id")
        tag.pop("product_uom_qty")
        tag.pop("date_order")
        tag.pop("_compute_partner_id")

        return tag

    def _get_orders_tags(self, reader):
        for line in reader:
            yield self._get_order_tag(line)

    def _get_order_tag_id(self, order_tag):
        order_id = self._search_by_external_id(order_tag["id"])

        # Se non esiste ancora l'order tag, lo creo...
        #
        if not order_id:
            fields = order_tag.keys()
            values = [order_tag.values()]

            result = self.env["crm.tag"].load(fields, values)

            if result["messages"]:
                print("")
                logger.error(
                    "Unable to properly import order tag with external ID '%s' due of:"
                    % order_tag["id"]
                )
                for message in result["messages"]:
                    print(" -> %s" % message["message"])

                print("")
                print(fields)
                print(values)
                print("")

                self.rollback()

                if self.is_debugging:
                    return

            elif result["ids"]:
                logger.debug(
                    "Imported order tag with external ID '%s': '%s'"
                    % (order_tag["id"], result["ids"])
                )

                self.commit()

                order_id = "%s" % result["ids"][0]

            else:
                self.rollback()

                raise Exception(
                    "I don't know why this is happening, but it's happening anyway!"
                )

        else:
            order_id = "%s" % order_id.id

        return order_id

    def _import_orders_tags(self, filename):
        print("")
        logger.info("Now starting importing orders tags...")

        reader = csv.reader(filename, delimiter=DELIMITER)
        reader.next()  # Skip first line...

        orders_tags = self._get_orders_tags(reader)

        for order_tag in orders_tags:
            tag_external_id = order_tag["_compute_tag_ids"]

            if tag_external_id not in self._cache_orders_tags_ids:
                tag_id = self._get_order_tag_id(
                    {"id": tag_external_id, "name": order_tag["name"]}
                )

                self._cache_orders_tags_ids[tag_external_id] = tag_id

            order_tag["tag_ids"] = [
                (4, 0, self._cache_orders_tags_ids[tag_external_id])
            ]

            order_tag.pop("_compute_tag_ids")

            fields = order_tag.keys()
            values = [order_tag.values()]
            result = self.env["sale.order"].load(fields, values)

            if result["messages"]:
                print("")
                logger.error(
                    "Unable to properly import sale order tag with external ID '%s' due of:"
                    % tag_external_id
                )
                for message in result["messages"]:
                    print(" -> %s" % message["message"])

                print("")
                print(fields)
                print(values)
                print("")

                self.rollback()

                if self.is_debugging:
                    return

            elif result["ids"]:
                logger.debug(
                    "Imported sale order tag with external ID '%s': '%s'"
                    % (tag_external_id, result["ids"])
                )

                self.commit()

            else:
                self.rollback()

                raise Exception(
                    "I don't know why this is happening, but it's happening anyway!"
                )

        logger.info("All sale orders tags has just been correctly imported!")

    def manage_args(self, args):
        parser = argparse.ArgumentParser()

        parser.add_argument("--partners")
        parser.add_argument("--addresses")
        parser.add_argument("--partners-tags")
        parser.add_argument("--orders")
        parser.add_argument("--orders-tags")

        parser.add_argument("--no-import", action="store_true")
        parser.add_argument("--associate", action="store_true")

        parser.add_argument("--debug", action="store_true")

        args, unknown = parser.parse_known_args(args)

        return args, unknown

    def rollback(self):
        self.env.cr.rollback()

    def commit(self):
        self.env.cr.commit()

    @environmentContextManager(manage_args_method="manage_args")
    def run(self, args, env):
        if args.debug:
            self.is_debugging = True

        try:
            self.env = env

            with cursor(env):
                self.state_model = self.env["res.country.state"]
                self.country_model = self.env["res.country"]

                self.country_italy = self.env.ref("base.it")

                if args.partners:
                    with open(args.partners, "rb") as filename:
                        self._import_partners(filename)

                if args.addresses:
                    with open(args.addresses, "rb") as filename:
                        self._import_addresses(filename)

                if args.partners_tags:
                    if not args.no_import:
                        with open(args.partners_tags, "rb") as filename:
                            self._import_partners_tags(filename)

                    if args.associate:
                        with open(args.partners_tags, "rb") as filename:
                            self._create_partners_tags_associations(filename)

                if args.orders:
                    with open(args.orders, "rb") as filename:
                        self._import_orders_lines(filename)

                if args.orders_tags:
                    with open(args.orders_tags, "rb") as filename:
                        self._import_orders_tags(filename)

                print("")
                logger.warning("Execution terminated! See log for details...")
                print("")

        except KeyboardInterrupt:
            print("")
            logger.warning("Execution stopped by the user!")
            print("")

        except Exception:
            logger.exception(
                "Something went wrong somewhere in the code! Now go to debugging!"
            )
class ImportContact_14(ImportFromChimp):
    def adjusted_fields(self, cls):
        fields = [f.name for f in attr.fields(cls)]

        fields = map(lambda x: x + "/id" if x.endswith("_id") else x, fields)
        return map(
            lambda x: x.replace("_xid", "_id") + "/.id"
            if x.endswith("_xid")
            else x,
            fields,
        )

    def run_batch(self, env, fln_name=None):
        logger.info("Start")

        self.env = env
        count = 0
        fields = [f.name for f in attr.fields(Partner)]
        try:
            with open(fln_name, "rt", encoding="utf-8") as filename:
                partners = self.get_partners(filename)
                '''
                partner_blocks = self.batch_generator(partners)
                for block in partner_blocks:
                    values = [attr.astuple(p) for p in block]
                    results = env["res.partner"].load(fields, values)
                    ids = self.set_ids_check_results(results)
                    count += len(ids)
                    logger.info("So far: %s", count)
                '''
        except Exception:
            logger.exception("caricamento fallito")
        finally:
            self.teardown()
    def batch_generator(self, iterable, recordnum=BATCH):
        source = iter(iterable)
        while True:
            batchiter = islice(source, recordnum)
            yield list(chain([next(batchiter)], batchiter))
    def get_partners(self, infile):
        reader = csv.reader(infile,delimiter=DELIMITER)
        next(reader)
        while True:
            line = next(reader)
            logger.info("line: %s", line)
            name = " ".join((line[1], line[2]))
            email = line[0].strip().lower()
            partner = Partner(
                firstname=name.title().strip(),
                email=email,
                id=self.external_id("contatti", email),
            )
            #yield partner
            fields = self.adjusted_fields(Partner)
            values = [attr.astuple(partner)]
            result = self.env["res.partner"].load(fields, values)
            ids = self.set_ids_check_results(result)
            print("Caricato", partner, "con id", ids)

    def slugify(self, value):
        if not isinstance(value, str):
            value = value.decode(ENC, "ignore")
        value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore")
        value = re.sub("[^/\w\s@-]", "", value.decode('utf-8')).strip().lower()
        return re.sub("[-\s/]+", "_", value)


    def external_id(self, target, field):
        key = self.slugify(field)
        ext_id = "feltricrm.%s_%s" % (target, key)
        return ext_id