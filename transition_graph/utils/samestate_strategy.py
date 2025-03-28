import hashlib

from transition_graph.nodes.state_node import StateNode


class AbstractSameStateStrategy:
    @staticmethod
    def is_same_state(dst_state_node: StateNode, src_state_node: StateNode):
        raise NotImplementedError()

class ComponentTreeHashSameStateStrategy(AbstractSameStateStrategy):
    @staticmethod
    def is_same_state(dst_state_node: StateNode, src_state_node: StateNode):
        tree1 = dst_state_node.component_tree
        tree2 = src_state_node.component_tree

        if tree1 is None or tree2 is None:
            return False

        tree1_hash = hashlib.md5(tree1.encode('utf-8')).hexdigest()
        tree2_hash = hashlib.md5(tree2.encode('utf-8')).hexdigest()

        return tree1_hash == tree2_hash

class InputTextExclusionSameStateStrategy(AbstractSameStateStrategy):
    @staticmethod
    def is_same_state(dst_state_node: StateNode, src_state_node: StateNode):
        """
        Check if two state nodes are in the same state by analyzing their component trees and excluding input text.
        :param dst_state_node: state node to compare with
        :param src_state_node: state node to compare against
        :return: True if the two state nodes are in the same state, False otherwise
        """
        from transition_graph.utils.layout_tree import LayoutTree, LayoutNode

        if dst_state_node.component_tree is None and src_state_node.component_tree is None:
            return True

        if dst_state_node.component_tree is None or src_state_node.component_tree is None:
            return False

        tree1 = LayoutTree(dst_state_node.component_tree)
        tree2 = LayoutTree(src_state_node.component_tree)

        def __is_same_node(node1: LayoutNode, node2: LayoutNode):
            if node1.tag != node2.tag:
                return False

            if node1.tag == "android.widget.EditText" or node1.tag == 'android.widget.AutoCompleteTextView':
                for key in node1.attributes:
                    if key == "bounds" or key == "text":
                        continue
                    if key not in node2.attributes or node1.attributes[key] != node2.attributes[key]:
                        return False
            else:
                for key in node1.attributes:
                    if key == "bounds":
                        continue
                    if key not in node2.attributes or node1.attributes[key] != node2.attributes[key]:
                        return False

            return True

        def __is_same_tree(node1: LayoutNode, node2: LayoutNode):
            if not __is_same_node(node1, node2):
                return False

            if len(node1.children) != len(node2.children):
                return False

            for child1, child2 in zip(node1.children, node2.children):
                if not __is_same_tree(child1, child2):
                    return False

            return True

        return __is_same_tree(tree1.root, tree2.root)

