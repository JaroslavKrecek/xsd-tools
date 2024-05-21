from argparse import ArgumentParser
import random

import xmlschema
from xmlschema.validators import (
    XsdElement,
    XsdAnyElement,
    XsdComplexType,
    XsdAtomicBuiltin,
    XsdSimpleType,
    XsdList,
    XsdUnion,
    XsdAtomicRestriction,
    XsdTotalDigitsFacet,
    XsdFractionDigitsFacet,
    XsdPatternFacets,
    XsdEnumerationFacets,
    XsdMinLengthFacet,
    XsdMaxLengthFacet
)

import rstr
from faker import Faker
from datetime import datetime


# sample data is hardcoded
def valsmap(v):
    # numeric types
    v['decimal'] = '-3.72'
    v['float'] = '-42.217E11'
    v['double'] = '+24.3e-3'
    v['integer'] = '-176'
    v['positiveInteger'] = '+3'
    v['negativeInteger'] = '-7'
    v['nonPositiveInteger'] = '-34'
    v['nonNegativeInteger'] = '35'
    v['long'] = '567'
    v['int'] = '109'
    v['short'] = '4'
    v['byte'] = '2'
    v['unsignedLong'] = '94'
    v['unsignedInt'] = '96'
    v['unsignedShort'] = '24'
    v['unsignedByte'] = '17'
    # time/duration types
    v['dateTime'] = '2004-04-12T13:20:00-05:00'
    v['date'] = '2004-04-12'
    v['gYearMonth'] = '2004-04'
    v['gYear'] = '2004'
    v['duration'] = 'P2Y6M5DT12H35M30S'
    v['dayTimeDuration'] = 'P1DT2H'
    v['yearMonthDuration'] = 'P2Y6M'
    v['gMonthDay'] = '--04-12'
    v['gDay'] = '---02'
    v['gMonth'] = '--04'
    # string types
    v['string'] = 'lol'
    v['normalizedString'] = 'The cure for boredom is curiosity.'
    v['token'] = 'There is no cure for curiosity.'
    v['language'] = 'en-US'
    v['NMTOKEN'] = 'A_BCD'
    v['NMTOKENS'] = 'ABCD 123'
    v['Name'] = 'myElement'
    v['NCName'] = '_my.Element'
    # magic types
    v['ID'] = 'IdID'
    v['IDREFS'] = 'IDrefs'
    v['ENTITY'] = 'prod557'
    v['ENTITIES'] = 'prod557 prod563'
    # oldball types
    v['QName'] = 'pre:myElement'
    v['boolean'] = 'true'
    v['hexBinary'] = '0FB8'
    v['base64Binary'] = '0fb8'
    v['anyURI'] = 'http://miaozn.github.io/misc'
    v['notation'] = 'asd'


# The XML Generator class
class GenXML:
    def __init__(self, xsd, elem, enable_choice, row_tag, row_count, unbounded_count, force_optional):
        self.xsd = xmlschema.XMLSchema(xsd)
        self.elem = elem
        self.enable_choice = enable_choice
        self.row_tag = row_tag
        self.row_count = int(row_count)
        self.unbounded_count = int(unbounded_count)
        self.root = False
        self.vals = {}
        self.faker = Faker()
        self.force_optional = bool(force_optional)

    # shorten the namespace
    def short_ns(self, ns):
        for k, v in self.xsd.namespaces.items():
            if k == '':
                continue
            if v == ns:
                return k
        return ''

    def use_short_ns(self, name):
        """Replaces long namespace, if used, with short one.

        If no short namespace is found, it's assumed a default (not specified) namespace is used.
        """

        if name[0] == '{':
            x = name.find('}')
            ns = name[1:x]
            short_ns = self.short_ns(ns)
            if short_ns == "":
                return name[x + 1:]
            return short_ns + ":" + name[x + 1:]
        return name

    @staticmethod
    def remove_ns(name):
        """Removes namespace from the name"""

        if name[0] == '{':
            x = name.find('}')
            return name[x + 1:]
        return name

    @staticmethod
    def print_header():
        """Prints XML header"""

        print("<?xml version=\"1.0\" encoding=\"UTF-8\" ?>")

    # put all defined namespaces as a string
    def ns_map_str(self):
        ns_all = ''
        for k, v in self.xsd.namespaces.items():
            if k == '':
                continue
            else:
                ns_all += 'xmlns:' + k + '=\"' + v + '\"' + ' '
        return ns_all

    # start a tag with name
    def start_tag(self, name, node):
        x = '<' + name
        if self.root:
            self.root = False
            x += ' ' + self.ns_map_str()

        # check whether node has attributes
        if len(node.attributes) > 0:
            for an_attrib in node.attributes:
                attrib_node = node.attributes[an_attrib]
                if isinstance(attrib_node.type, XsdAtomicRestriction):
                    attrib_value = self.generate_string(attrib_node.type)
                    x += f' {attrib_node.name}="{attrib_value}"'

        x += '>'
        return x

    # end a tag with name
    def end_tag(self, name):
        return '</' + name + '>'

    @staticmethod
    def generate_decimal(node_type) -> str:
        """Generates decimal string within restricted number of digits before and after decimal point
        """

        total_digits = 20
        fraction_digits = 5
        for aRestriction in node_type.validators:
            if isinstance(aRestriction, XsdTotalDigitsFacet):
                total_digits = int(aRestriction.value)
            elif isinstance(aRestriction, XsdFractionDigitsFacet):
                fraction_digits = int(aRestriction.value)
        value_digits = random.randint(1, total_digits)
        value_fraction_digits = random.randint(0, min(value_digits - 1, fraction_digits))
        if value_fraction_digits == 0:
            return str(random.randint(0, 10 ** value_digits))
        else:
            return str(
                f"{random.randint(0, 10 ** (value_digits - value_fraction_digits))}.{random.randint(0, 10 ** value_fraction_digits)}")

    def generate_string(self, node_type: XsdAtomicRestriction) -> str:
        """Generates string applying following types of facets:
         - RegEx pattern
         - enumeration
         - min length
         - max length
        """

        s_value = self.faker.text()
        min_len = 1
        max_len = 50
        b_mod_len = False
        if len(node_type.facets) > 0:
            for aFacet in node_type.facets:
                if isinstance(node_type.facets[aFacet], XsdPatternFacets):
                    reg_ex_pattern = '[a-zA-Z0-9 ]{20}'
                    for aPattern in node_type.patterns:
                        reg_ex_pattern = aPattern.get('value')
                    s_value = rstr.xeger(reg_ex_pattern)
                elif isinstance(node_type.facets[aFacet], XsdEnumerationFacets):
                    if len(node_type.enumeration) > 0:
                        enum_ix = random.randint(0, len(node_type.enumeration) - 1)
                        s_value = node_type.enumeration[enum_ix]
                elif isinstance(node_type.facets[aFacet], XsdMinLengthFacet):
                    min_len = node_type.min_length
                elif isinstance(node_type.facets[aFacet], XsdMaxLengthFacet):
                    max_len = node_type.max_length
                    b_mod_len = True
                else:
                    s_value = '*** Unexpected facet ***'

        if b_mod_len:
            a_len = random.randint(min_len, max_len)
            s_value = s_value[:a_len]
        return s_value

    @staticmethod
    def generate_boolean(node_type: XsdAtomicRestriction) -> str:
        """Generates random value of true or false"""

        if random.randint(0, 1) == 1:
            return 'true'

        return 'false'

    def generate_datetime(self, node_type: XsdAtomicRestriction) -> str:
        """Generates random dateTime between a year ago and a year into future"""

        rand_datetime = self.faker.date_time_between(start_date='-1y', end_date='+1y')
        s_ret_val = datetime.strftime(rand_datetime, '%Y-%m-%dT%H:%M:%S.%f')
        return str(f"{s_ret_val[:23]}Z")

    def generate_date(self, node_type: XsdAtomicRestriction) -> str:
        """Generates random date between a year ago and a year into the future"""

        random_datetime = self.faker.date_between(start_date='-1y', end_date='+1y')
        return datetime.strftime(random_datetime, '%Y-%m-%d')

    def generate_gregorian_year(self, node_type) -> str:
        """Generates a random year between 20 years ago and 20 year into the future"""

        random_datetime = self.faker.date_between(start_date='-20y', end_date='+20y')
        return datetime.strftime(random_datetime, '%Y')

    def genval(self, name, node_type):
        """Generates random data for the element contents"""

        if isinstance(node_type, XsdAtomicRestriction):
            base_type = self.remove_ns(node_type.base_type.name)
            if base_type == "decimal":
                return self.generate_decimal(node_type)
            elif base_type == "string":
                return self.generate_string(node_type)
            elif base_type == 'boolean':
                return self.generate_boolean(node_type)
            elif base_type == 'dateTime':
                return self.generate_datetime(node_type)
            elif base_type == 'date':
                return self.generate_date(node_type)
            elif base_type == 'gYear':
                return self.generate_gregorian_year(node_type)
            elif base_type == 'time':
                return self.generate_datetime(node_type)[11:]
        elif isinstance(node_type, XsdAtomicBuiltin):
            content_type = self.remove_ns(node_type.name)
            if content_type == 'decimal':
                return self.generate_decimal(node_type)

        print('<!-- Hardcoded content value -->')
        name = self.remove_ns(name)
        if name in self.vals:
            return self.vals[name]
        return 'ERROR !'

    # print a group
    def group2xml(self, g):
        model = str(g.model)
        model = self.remove_ns(model)

        # get list of group items
        nextg = g._group
        y = len(nextg)
        if y == 0:
            print('<!--empty-->')
            return

        # print('<!--START:[' + model + ']-->')
        if self.enable_choice and model == 'choice':
            # print('<!-- a random item from a [choice] group with size=' + str(y) + '-->')
            ixChoice = random.randint(0, y - 1)
            ng = nextg[ixChoice]
            if isinstance(ng, XsdElement):
                self.node2xml(ng)
            elif isinstance(ng, XsdAnyElement):
                self.node2xml(ng)
            else:
                self.group2xml(ng)
        else:
            # print('<!--next ' + str(y) + ' items are in a [' + model + '] group-->')
            for ng in nextg:
                if isinstance(ng, XsdElement):
                    self.node2xml(ng)
                elif isinstance(ng, XsdAnyElement):
                    self.node2xml(ng)
                else:
                    self.group2xml(ng)
        # print('<!--END:[' + model + ']-->')

        # print a node

    def getContentType(self, node):
        aBaseNode = node.type.content
        while aBaseNode.is_simple() is False:
            aBaseNode = aBaseNode.base_type
        return aBaseNode

    def node2xml(self, node):
        # set random number of repeatable elements
        min_occur = 1  # default is mandatory
        max_occur = 1  # default is not repeatable

        if not self.force_optional:
            if node.min_occurs is not None:  # is min_occurs specified?
                # print('<!--next 1 item is optional (minOccurs = 0)-->')
                min_occur = node.min_occurs

        if node.max_occurs is not None:  # is max_occurs specified?
            if node.max_occurs == 'unbounded':
                max_occur = self.unbounded_count
                print(f'<!-- next is repeatable (maxOccurs == unbounded)-->')
            else:
                if node.max_occurs > 1:
                    print(f'<!-- next element is repeatable (maxOccurs == {node.max_occurs})-->')
                if self.remove_ns(node.name) == self.row_tag:
                    # handle row_tag and row_count when number of rows is limited by XSD
                    max_occur = min(self.row_count, node.max_occurs)
                else:
                    # handle other repeatable sections
                    max_occur = min(node.max_occurs, self.unbounded_count)
        else:
            # xmlschema doesn't seem to handle 'unbounded' string in the node.max_occurs property
            if node.schema_elem.attrib['maxOccurs'] == 'unbounded':
                max_occur = self.unbounded_count
                print(f'<!-- next is repeatable (maxOccurs == unbounded)-->')
                # handle row_tag and row_count when number of rows is unbounded in XSD
                if self.remove_ns(node.name) == self.row_tag:
                    max_occur = self.row_count
            else:
                print('<!-- maxOccurs attribute not found -->')

        # handle row_tag and row_count
        if self.remove_ns(node.name) == self.row_tag:
            no_occurance = max_occur
        else:
            no_occurance = random.randint(min_occur, max_occur)

        for i in range(no_occurance):
            if isinstance(node, XsdAnyElement):
                print('<_ANY_/>')

            if isinstance(node.type, XsdComplexType):
                n = self.use_short_ns(node.name)
                if node.type.is_simple() or node.type.content_type_label == 'simple':
                    # complex type with simple content
                    # print('<!--simple content in XsdComplexType-->')
                    if isinstance(node.type.content, XsdAtomicRestriction):
                        tp = str(node.type.content.base_type)
                        a_content_type = node.type.content.base_type
                    else:
                        tp = str(node.type.content_type)
                        a_content_type = node.type.content_type
                    # treat as simple - this a simple base type modified
                    # tp2 = str(self.getContentType(node))
                    # tp = str(node.type.base_type)
                    print(self.start_tag(n, node) + self.genval(tp, a_content_type) + self.end_tag(n))
                else:
                    # print('<!--complex content-->')
                    print(self.start_tag(n, node))
                    self.group2xml(node.type.content)
                    print(self.end_tag(n))
            elif isinstance(node.type, XsdAtomicBuiltin):
                n = self.use_short_ns(node.name)
                tp = str(node.type.name)
                print(self.start_tag(n, node) + self.genval(tp) + self.end_tag(n))
            elif isinstance(node.type, XsdSimpleType):
                n = self.use_short_ns(node.name)
                if isinstance(node.type, XsdList):
                    print('<!--simpletype: list-->')
                    tp = str(node.type.item_type.name)
                    print(self.start_tag(n, node) + self.genval(tp) + self.end_tag(n))
                elif isinstance(node.type, XsdUnion):
                    print('<!--simpletype: union.-->')
                    print('<!--default: using the 1st type-->')
                    tp = str(node.type.member_types[0].base_type.name)
                    print(self.start_tag(n, node) + self.genval(tp) + self.end_tag(n))
                else:
                    tp = str(node.type.base_type.name)
                    print(self.start_tag(n, node) + self.genval(tp, node.type) + self.end_tag(n))
            else:
                print('ERROR: unknown type: ' + node.type)

    # setup and print everything
    def run(self):
        valsmap(self.vals)
        self.print_header()
        self.node2xml(self.xsd.elements[self.elem])


##############


def main():
    parser = ArgumentParser()
    parser.add_argument("-s", "--schema", dest="xsdfile", required=True,
                        help="select the xsd used to generate xml")
    parser.add_argument("-e", "--element", dest="element", required=True,
                        help="select an element to dump xml")
    parser.add_argument("-c", "--choice",
                        action="store_true", dest="enable_choice", default=True,
                        help="enable generating a random <choice> element from options")
    parser.add_argument("-rtag", "--rowtag",
                        dest="row_tag", default="Rpt",
                        help="Control which element is classed as a row. (Combined with --rwcount)")
    parser.add_argument("-rcnt", "--rowcount",
                        dest="row_count", default="50",
                        help="If --rowtag is specified, this controls number of its elements generated")
    parser.add_argument("-ucnt", "--unboundedcount",
                        dest="unbounded_count", default="10",
                        help="Limit to max number of unbounded elements generated.")
    parser.add_argument("-fopt", "--forceoptional",
                        dest="force_optional", default="False",
                        help="Force creation of optional elements. (True / False)")
    args = parser.parse_args()

    # construct and initialise XML Generator object
    generator = GenXML(args.xsdfile, args.element, args.enable_choice,
                       args.row_tag, args.row_count, args.unbounded_count, args.force_optional)

    # run the XML generation procedure
    generator.run()


if __name__ == "__main__":
    main()
