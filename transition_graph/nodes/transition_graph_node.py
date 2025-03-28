class TransitionGraphNode:
    """
    A transition graph node represents the whole transition graph. It employs the concept of HFSM(Hierarchical Finite State Machine) to model the transition graph. The transition graph is composed of a set of page nodes, each of which represents a page in the application. Each page node contains a set of state nodes that are present on the page, and a set of transitions that can be taken from the page. The transitions are represented as tuples of the event that triggers the transition, the source state node, and the target state node.

    Attributes:
        - start_page: the start page node of the transition graph
        - start_state: the start state node of the transition graph
        - end_state: the end state node of the transition graph
        - end_page: the end page node of the transition graph
        - page_nodes: a list of page nodes in the transition graph
    """

    def __init__(self):
        from transition_graph.nodes.page_node import PageNode
        from transition_graph.nodes.state_node import StateNode

        self.start_page = None
        self.start_state = None
        self.end_state = StateNode("end_state_node", None, None) # Dummy end state, id is always 0
        self.end_page = PageNode("end", None) # Dummy end page, id is always 0
        self.end_page.add_state_node(self.end_state)
        self.page_nodes = []
        self.internal_state_nodes = []
        self.add_page_node(self.end_page)

    def add_page_node(self, page_node):
        self.page_nodes.append(page_node)

    def set_start_state(self, state_node):
        self.start_state = state_node
        self.start_page = state_node.parent_page_node

    def get_end_state(self):
        return self.end_state

    def add_internal_state_node(self, internal_state_node):
        self.internal_state_nodes.append(internal_state_node)

    def to_dict(self):
        return {
            "start_page": self.start_page.to_dict(),
            "start_state": self.start_state.to_dict(),
            "end_state": self.end_state.to_dict(),
            "end_page": self.end_page.to_dict(),
            "page_nodes": [page_node.to_dict() for page_node in self.page_nodes],
            "internal_state_nodes": [internal_state_node.to_dict() for internal_state_node in self.internal_state_nodes]
        }