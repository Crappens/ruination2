__author__ = "bcrysler"

import json

from flask import request, jsonify
from flask.ext.restful import Resource
from lxml import etree
from app.flowing.models import SVGDoc


class Validation(Resource):

    def post(self):
        xsd_parsed = etree.parse("./svg.xsd")
        xsd_schema = etree.XMLSchema(xsd_parsed)

        spread = json.loads(request.data)["svg"]
        spread_parsed = SVGDoc(etree.fromstring(spread))

        count = 0
        while True:
            if count == 10:
                data = {"svg": "unfixable"}
                resp = jsonify(data)
                resp["headers"] = {"Content-Type": "application/json",
                                   "Access-Control-Allow-Origin": "*"}
                resp.status_code = 400
                return resp
            blob = xsd_schema.validate(spread_parsed.original)

            errors = [x for x in xsd_schema.error_log if "SCHEMAV_CVC_COMPLEX_TYPE_3_2_1" != x.type_name and "SCHEMAV_ELEMENT_CONTENT" != x.type_name]

            if blob is True or len(errors) == 0:
                data = {"svg": self.stringify(etree.tostring(spread_parsed.original, pretty_print=True))}
                resp = jsonify(data)
                resp.status_code = 200
                return resp
            else:
                spread_parsed.new_svg_tag()
                spread_parsed.fix_tags()
                spread_parsed.remove_pattern_tag()

                xsd_schema.validate(spread_parsed.original)
            count += 1


    def stringify(self, prettified):
        finalized = prettified.replace('\n', '').replace('\t', '')
        while ' <' in finalized or '> ' in finalized:
            finalized = finalized.replace(' <', '<')
            finalized = finalized.replace('> ', '>')
        return finalized
