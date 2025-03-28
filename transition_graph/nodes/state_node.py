class AbstractStateNode:
    counter = 0

    def __init__(self, name):
        self.name = name
        self.id = AbstractStateNode.counter
        self.transitions = dict()
        AbstractStateNode.counter += 1

    def to_dict(self) -> dict:
        raise NotImplementedError

class StateNode(AbstractStateNode):
    """
    A class representing a normal state node in the transition graph.

    Attributes:
        - name: the name of the state node
        - id: the unique identifier of the state node
        - component_tree: the component tree of the state node, represented as an XML-like string
        - screenshot_path: the path to the screenshot of the state node
        - transitions: a list of transitions from the state node to other state nodes
            - each transition is a tuple of the form (event, target_node)
            - target_node is the state node that the transition leads to
        - parent_page_node: the parent page node of the state node
        - available_events: a list of events that can be triggered in the state node
        - visited_events: a list of events that have been triggered in the state node
    """

    def __init__(self, name, component_tree, screenshot_path):
        from transition_graph.utils.event_parser import get_all_events_in_component_tree

        super(StateNode, self).__init__(name)
        self.component_tree = component_tree
        self.screenshot_path = screenshot_path
        self.available_events = get_all_events_in_component_tree(self, self.component_tree) if self.component_tree else []
        self.visited_events = []
        self.parent_page_node = None

    def add_transition(self, event, target_node):
        """
        Add a transition from the state node to the target node.
        :param event: The event that triggers the transition.
        :param target_node: The target state node that the transition leads to.
        :return: The internal state node produced by the transition. If no internal state node is produced, return None.
        """
        from transition_graph.events.event import InternalEvent

        # self.transitions.append((event, target_node))
        # if not in the dictionary, add it
        # if in the dictionary, create a new InternalStateNode, update the dictionary.
        if event not in self.transitions or self.transitions[event] == target_node:
            self.transitions[event] = target_node
            return None
        elif isinstance(self.transitions[event], InternalStateNode):
            # add a new transition from the internal node to the target node
            internal_node = self.transitions[event]
            internal_node.add_transition(InternalEvent(internal_node), target_node)
        else:
            # create a new InternalStateNode
            previous_target_node = self.transitions[event]
            internal_node = InternalStateNode("internal_state_node_from_" + self.name)
            internal_node.add_transition(InternalEvent(internal_node), previous_target_node)
            internal_node.add_transition(InternalEvent(internal_node), target_node)
            self.transitions[event] = internal_node
            return internal_node


    def set_parent_page_node(self, parent_page_node):
        self.parent_page_node = parent_page_node

    def add_visited_event(self, event):
        if event in self.visited_events:
            print(f"StateNode visit Warning: duplicated visit event ({event}) in StateNode ({self.id})")
            return
        if event not in self.available_events:
            print(f"StateNode visit Warning: event ({event}) not in available events of StateNode ({self.id})")
            return
        self.visited_events.append(event)

    def get_unvisited_events(self):
        return [event for event in self.available_events if event not in self.visited_events]

    def get_visited_events(self):
        return self.visited_events


    def to_dict(self):
        return {
            "name": self.name,
            "id": self.id,
            "component_tree": self.component_tree,
            "screenshot_path": self.screenshot_path,
            "transitions": [{"event": event.to_dict(), "target_state_node_id":target_node.id} for event, target_node in self.transitions.items()],
            "parent_page_node_id": self.parent_page_node.id,
            "available_events": [event.to_dict() for event in self.available_events],
            "visited_events": [event.to_dict() for event in self.visited_events]
        }

class InternalStateNode(AbstractStateNode):
    """
    A class representing an internal state node in the transition graph.
    For example, a state node that represents a system state or a state node that is not reachable from the UI.

    Attributes:
        - name: the name of the state node
        - id: the unique identifier of the state node
        - transitions: a list of transitions from the state node to other state nodes
            - each transition is a tuple of the form (event, target_node)
            - event is also an InternalEvent object
            - target_node is the state node that the transition leads to

    NOTE:
        Internal state nodes should not be added manually. They are created automatically when adding transitions to state nodes.
        Internal state nodes don't belong to any page node.
    """

    def __init__(self, name):
        super(InternalStateNode, self).__init__(name)

    def add_transition(self, event, target_node):
        # self.transitions.append((event, target_node))
        if event not in self.transitions:
            self.transitions[event] = target_node
        else:
            print("InternalStateNode Error: duplicated event")
            raise ValueError

    def to_dict(self):
        return {
            "name": self.name,
            "id": self.id,
            "transitions": [{"event": event.to_dict(), "target_state_node_id": target_node.id} for event, target_node in self.transitions.items()]
        }