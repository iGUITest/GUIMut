import numpy as np
from scipy.optimize import linear_sum_assignment


class AbstractBelongingStrategy:
    def belongs_to_which_page(self, state_node, page_nodes):
        """
        This interface method should be implemented by all subclasses.
        It should return the page node that the given state node belongs to, using certain strategies.
        :param state_node: The state node to be checked
        :param page_nodes: A list of page nodes to be checked against
        :return: A page node that the state node belongs to. If the state node does not belong to any page, return None.
        """
        raise NotImplementedError()

class ComponentTreeSimilarityBelongingStrategy(AbstractBelongingStrategy):
    from transition_graph.nodes.state_node import StateNode
    from transition_graph.nodes.page_node import PageNode
    from transition_graph.utils.layout_tree import LayoutTree


    def __init__(self, threshold):
        self.threshold = threshold
        print(f"Using ComponentTreeSimilarityBelongingStrategy. [threshold: {threshold}]")

    def __tree_similarity(self, tree1: LayoutTree, tree2: LayoutTree):
        """
        Calculate the similarity between two component trees using the Hungarian algorithm.
        :param tree1: The first component tree to compare. The type of tree1 is LayoutTree.
        :param tree2: The second component tree to compare. The type of tree2 is LayoutTree.
        :return: A float value representing the similarity between the two trees.
        """
        memo = {}

        def __similarity(t1, t2):
            if t1 is None and t2 is None:
                return 1.0
            if t1 is None or t2 is None:
                return 0.0
            if (id(t1), id(t2)) in memo:
                return memo[(id(t1), id(t2))]

            # Similarity of Node Value
            value_sim = self.__node_value_similarity(t1, t2)

            children1 = t1.children
            children2 = t2.children

            if not children1 and not children2:
                memo[(id(t1), id(t2))] = value_sim
                return value_sim

            n = len(children1)
            m = len(children2)
            if n == 0 or m == 0:
                child_sim = 0.0
            elif n == 0 and m == 0:
                child_sim = 1.0
            else:
                sim_matrix = np.zeros((n, m))
                for i in range(n):
                    for j in range(m):
                        sim_matrix[i][j] = __similarity(children1[i], children2[j])

                # Hungarian Algorithm
                row_ind, col_ind = linear_sum_assignment(-sim_matrix)
                child_sim = sim_matrix[row_ind, col_ind].sum() / max(n, m)

            # Average Similarity with Node Value and Children
            # Weights are 0.5 for each
            self_value_weight = 0.1
            total_sim = self_value_weight * value_sim + (1 - self_value_weight) * child_sim
            memo[(id(t1), id(t2))] = total_sim
            return total_sim

        return __similarity(tree1.root, tree2.root)

    @staticmethod
    def __node_value_similarity(node1, node2):
        """
        Calculate the similarity of two nodes based on their tag and attributes.
        :param node1: The first node to compare.
        :param node2: The second node to compare.
        :return: A float value representing the similarity between the two nodes.
        """
        if node1.tag != node2.tag:
            return 0.0

        attr1 = node1.attributes
        attr2 = node2.attributes

        # exclude 'bounds' attribute
        common_keys = set(attr1.keys()) & set(attr2.keys()) - {"bounds"}
        if not common_keys:
            return 0.0

        value_sim = 0.0
        for key in common_keys:
            if attr1[key] == attr2[key]:
                value_sim += 1.0

        return value_sim / len(common_keys)

    def belongs_to_which_page(self, state_node: StateNode, page_nodes: list[PageNode]):
        from transition_graph.utils.layout_tree import LayoutTree
        from transition_graph.nodes.state_node import InternalStateNode

        page_similarity = []
        state_node_layout_tree = LayoutTree(state_node.component_tree)

        for page_node in page_nodes:
            _sum = 0
            _count = 0
            for target_state_node in page_node.state_nodes:
                if isinstance(target_state_node, InternalStateNode) or target_state_node.component_tree is None:
                    continue
                target_state_node_layout_tree = LayoutTree(target_state_node.component_tree)
                _sum += self.__tree_similarity(state_node_layout_tree, target_state_node_layout_tree)
                _count += 1
            avg = _sum / _count if _count > 0 else 0
            page_similarity.append([page_node, avg])

        page_similarity.sort(key=lambda x: x[1], reverse=True)

        # Check if the highest similarity is above the threshold
        if page_similarity[0][1] > self.threshold:
            return page_similarity[0][0]
        else:
            return None