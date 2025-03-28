import xml.etree.ElementTree as ET

class LayoutNode:
    def __init__(self, element):
        self.tag = element.tag
        self.attributes = element.attrib
        self.children = []

    def add_child(self, child):
        self.children.append(child)

    def __str__(self):
        return f"{self.tag} ({len(self.children)} children)"


class LayoutTree:
    def __init__(self, xml):
        self.root = self.parse(xml)

    def parse(self, xml):
        root = ET.fromstring(xml)
        return self._build_tree(root)

    def _build_tree(self, element):
        node = LayoutNode(element)

        for child in element:
            child_node = self._build_tree(child)
            node.add_child(child_node)

        return node

    def print_tree(self, node=None, level=0):
        if node is None:
            node = self.root

        indent = "  " * level
        print(f"{indent}{node.attributes}")

        for child in node.children:
            self.print_tree(child, level + 1)

    def find_nodes_by_attribute(self, attr_name, attr_value, node=None):
        if node is None:
            node = self.root

        results = []

        if attr_name in node.attributes and node.attributes[attr_name] == attr_value:
            results.append(node)

        for child in node.children:
            results.extend(self.find_nodes_by_attribute(attr_name, attr_value, child))

        return results