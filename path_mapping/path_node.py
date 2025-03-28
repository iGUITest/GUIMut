class AbstractPathNode:
    def __init__(self, state, event, next_path_node=None):
        self.state = state
        self.event = event
        self.next_path_node = next_path_node

class PathNode(AbstractPathNode):
    """
    PathNode is a concrete implementation of AbstractPathNode.
    It represents a node in the path graph, containing a state and an event.
    """

    def __init__(self, state, event, next_path_node=None):
        from transition_graph.nodes.state_node import StateNode
        from transition_graph.events.event import InternalEvent
        if not isinstance(state, StateNode) or isinstance(event, InternalEvent):
            raise ValueError("PathNode can only be created with an AbstractStateNode.")
        super(PathNode, self).__init__(state, event, next_path_node)

class InternalPathNode(AbstractPathNode):
    """
    InternalPathNode is a concrete implementation of AbstractPathNode.
    It represents a node in the path graph that is not reachable from the UI.
    """

    def __init__(self, state, event, next_path_node=None):
        from transition_graph.nodes.state_node import InternalStateNode
        from transition_graph.events.event import InternalEvent
        if not isinstance(state, InternalStateNode) or (not isinstance(event, InternalEvent) and event is not None):
            raise ValueError("InternalPathNode can only be created with an InternalStateNode.")
        super(InternalPathNode, self).__init__(state, event, next_path_node)