from argparse import ArgumentParser

import xmlschema
from xmlschema.validators import (
    XsdElement,
    XsdAnyElement,
    XsdComplexType,
    XsdAtomicBuiltin,
    XsdSimpleType,
    XsdAtomicRestriction
)
import sys


class XsdWalker:
    def __init__(self, xsd, elem, row_tag, output_file):
        self.xsd = xmlschema.XMLSchema(xsd)
        self.elem = elem
        self.row_tag = row_tag
        self.output_file = output_file

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

    def print_header(self):
        """Prints header"""
        print(f"Flattener config for: {self.xsd.name}")

    def walk_complex_node(self, g, xpath, column_prefix):
        """
        Walk a group / complex node
        :param g: current node to walk
        :param xpath: xpath to the node
        :param column_prefix: current column_prefix for flattened column names
        :return:
        """

        # get list of group items
        next_group = g._group
        y = len(next_group)
        if y == 0:
            print(f'Error: Node group {g.name} is empty.')
            return

        for ng in next_group:
            if isinstance(ng, XsdElement):
                self.walk_node(ng, xpath, column_prefix)
            elif isinstance(ng, XsdAnyElement):
                self.walk_node(ng, xpath, column_prefix)
            else:
                self.walk_complex_node(ng, xpath, column_prefix)

    def get_content_type(self, node):
        base_node = node.type.content
        while base_node.is_simple() is False:
            base_node = base_node.base_type
        return base_node

    def walk_node(self, node, xpath, column_prefix):
        """
        Walks the given node recursively to child elements.
        Handles choice by calling each from the choice
        Handles repeatable occurrence by printing []
        :param
        node: node to walk
        column_prefix: text to be used as prefix for current node and all child nodes
        :return: none
        """

        # increase depth of the xpath
        node_name = self.remove_ns(node.name)
        xpath += '/'+node_name

        # check whether we're in the subtree of the rowtag parameter
        if node_name == self.row_tag:
            column_prefix = node_name

        ix_row_tag = xpath.find('/'+self.row_tag+'/')
        if ix_row_tag > -1:
            # add current node name to the column prefix
            column_prefix += '.'+node_name

        # check whether the node is repeatable
        repeatable = False
        if node.max_occurs is not None:  # is max_occurs specified?
            if node.max_occurs != 1:
                print(f'\nNote: repeatable node {column_prefix}[{node.min_occurs}-{node.max_occurs}]')
                # column_prefix += '[]'
                repeatable = True
        # xmlschema doesn't seem to handle 'unbounded' string in the node.max_occurs property
        elif node.schema_elem.attrib['maxOccurs'] == 'unbounded':
            print(f'\nNote: repeatable node {column_prefix}[{node.min_occurs}-unbounded]')
            # column_prefix += '[]'
            repeatable = True

        # handle XsdAnyElement
        if isinstance(node, XsdAnyElement):
            print('Warning: <_ANY_/> element found.')

        # check whether node has attributes
        content_suffix = ''
        if len(node.attributes) > 0:
            for an_attrib in node.attributes:
                attrib_node = node.attributes[an_attrib]
                if isinstance(attrib_node.type, XsdAtomicRestriction):
                    print(f'{column_prefix}.{attrib_node.name};{xpath}')
                    content_suffix = '.VALUE'

        # check whether node is of complex type
        if isinstance(node.type, XsdComplexType):
            if node.type.is_simple() or node.type.content_type_label == 'simple':
                if len(column_prefix)>0:
                    # complex type with simple content => print column name
                    print(f'{column_prefix}{content_suffix};{xpath}')
            else:
                # complex node
                self.walk_complex_node(node.type.content, xpath, column_prefix)
        elif len(column_prefix)>0:
            if isinstance(node.type, XsdAtomicBuiltin):
                # atomic node => print column name
                print(f'{column_prefix}{content_suffix};{xpath}')
            elif isinstance(node.type, XsdSimpleType):
                print(f'{column_prefix}{content_suffix};{xpath}')
            else:
                print('ERROR: unknown type: ' + node.type)

        if repeatable:
            print('')

    # print everything
    def run(self):
        """
        Opens the output stream into a file if required.
        Prints header row
        Call the walker to generate flattened column names
        :return:
        """

        stdout_fileno = sys.stdout
        if len(self.output_file)>0:
            # redirect standard output to a file
            sys.stdout = open(self.output_file, 'w')

        self.print_header()

        # walk down from the root (defined) element node
        self.walk_node(self.xsd.elements[self.elem], '', '')

        # close file if opened
        if len(self.output_file)>0:
            sys.stdout.close()
            sys.stdout = stdout_fileno

##############


def main():
    parser = ArgumentParser()
    parser.add_argument("-s", "--schema", dest="xsdfile", required=True,
                        help="select the xsd used to generate xml")
    parser.add_argument("-e", "--element", dest="element", required=True,
                        help="select an element to dump xml")
    parser.add_argument("-rtag", "--rowtag",
                        dest="row_tag", default="Rpt",
                        help="Control which element is classed as a row. (Combined with --rwcount)")
    parser.add_argument("-o", "--output_file", dest="output_file", required=False,
                        default="",
                        help="Specify name of output file or leave empty to print to console.")

    args = parser.parse_args()

    # construct and initialise XsdWalker object
    generator = XsdWalker(args.xsdfile, args.element, args.row_tag, args.output_file)

    # traverse the XSD - run the generation procedure
    generator.run()


if __name__ == "__main__":
    main()
