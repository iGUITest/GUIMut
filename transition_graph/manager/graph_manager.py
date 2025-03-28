import os

import yaml
import json

from transition_graph.nodes.page_node import PageNode
from transition_graph.utils.belonging_strategy import ComponentTreeSimilarityBelongingStrategy
from transition_graph.utils.mock_strategy import MockStrategy
from transition_graph.utils.samestate_strategy import ComponentTreeHashSameStateStrategy


class GraphManager:
    from transition_graph.nodes.state_node import StateNode
    from transition_graph.nodes.page_node import PageNode
    from transition_graph.events.event import AbstractEvent
    from transition_graph.nodes.state_node import AbstractStateNode

    currentGraph = None
    same_state_strategy = None
    belonging_strategy = None

    def __init__(self, yaml_file_path):
        from transition_graph.nodes.transition_graph_node import TransitionGraphNode

        self.currentGraph = TransitionGraphNode()
        yaml_file = open(yaml_file_path, "r")
        config = yaml.safe_load(yaml_file)
        yaml_file.close()

        # Load the strategies
        if config["sameStateStrategy"]["type"] == "hash":
            self.same_state_strategy = ComponentTreeHashSameStateStrategy()

        if config["belongingStrategy"]["type"] == "tree_similarity":
            threshold = config["belongingStrategy"]["threshold"]
            self.belonging_strategy = ComponentTreeSimilarityBelongingStrategy(float(threshold))

        # Load save path
        self.save_path = config["graphDir"]

        print("GraphManager initialized")

    def set_start_state(self, start_state: StateNode):
        self.currentGraph.set_start_state(start_state)

    def get_start_state(self):
        return self.currentGraph.start_state

    def get_start_page(self):
        return self.currentGraph.start_page

    def add_page_node(self, page_node: PageNode):
        self.currentGraph.add_page_node(page_node)

    @staticmethod
    def add_state_to_page(state_node: AbstractStateNode, page_node: PageNode):
        page_node.add_state_node(state_node)

    def belongs_to_which_page(self, state_node: StateNode, current_activity):
        target_page_node = self.belonging_strategy.belongs_to_which_page(state_node, self.currentGraph.page_nodes)
        if target_page_node is None:
            # If the state node does not belong to any page, create a new page node
            target_page_node = PageNode("page", current_activity)
            self.add_page_node(target_page_node)

        return target_page_node

    def add_transition(self, event: AbstractEvent, source_state_node: StateNode, target_state_node: StateNode):
        from transition_graph.events.event import InternalEvent

        if isinstance(event, InternalEvent):
            print("Internal event Error: it should not be added manually.")
            raise ValueError
        new_internal_state_node = source_state_node.add_transition(event, target_state_node)
        if new_internal_state_node is not None:
            self.currentGraph.add_internal_state_node(new_internal_state_node)

    def add_new_state(self, new_state_node: StateNode, source_state_node: StateNode, event: AbstractEvent, current_activity):
        """
        Add a new state to the graph. An important method to maintain the graph.
        If the new state is not in the graph, it will be added to the graph.

        :param new_state_node: The new state node to be added.
        :param source_state_node: The source state node.
        :param event: The event that triggers the transition.
        :param current_activity: The current activity of the new state node.
        :return: The new state node, or the existing one.
        """
        # If the new state is the first state in the graph, set it as the start state
        if self.currentGraph.start_state is None:
            target_page_node = self.belongs_to_which_page(new_state_node, current_activity)
            self.add_state_to_page(new_state_node, target_page_node)
            self.set_start_state(new_state_node)
            return new_state_node

        # The new state node is the end state
        if new_state_node == self.currentGraph.get_end_state():
            self.add_transition(event, source_state_node, new_state_node)
            return new_state_node

        # Check if the new state node is already in the graph
        state_node = self.find_state(new_state_node)
        if state_node is not None:
            # If the new state node is already in the graph, add the transition
            self.add_transition(event, source_state_node, state_node)
            return state_node

        # If the new state node is not in the graph, add it to the graph
        target_page_node = self.belongs_to_which_page(new_state_node, current_activity)
        self.add_state_to_page(new_state_node, target_page_node)
        self.add_transition(event, source_state_node, new_state_node)

        return new_state_node

    def find_state(self, new_state_node: StateNode):
        for page_node in self.currentGraph.page_nodes:
            for state_node in page_node.state_nodes:
                if self.same_state_strategy.is_same_state(new_state_node, state_node):
                    return state_node
        return None

    @staticmethod
    def visit_event(event: AbstractEvent, state_node: StateNode):
        state_node.add_visited_event(event)

    def get_end_state(self):
        return self.currentGraph.get_end_state()

    def save_graph_to_file(self):
        """
        Save the current graph to a file.
        :return: Boolean, whether the graph is saved successfully.

        Note: If you call this method, old saved graph will be deleted.
        """
        # Delete the old files
        if os.path.exists(self.save_path):
            os.system(f"rm -rf {self.save_path}")
        os.makedirs(self.save_path, exist_ok=True)

        # Use json to save the graph
        graph_dict = self.currentGraph.to_dict()
        try:
            path = os.path.join(self.save_path, "graph.json")
            with open(path, "w") as f:
                json.dump(graph_dict, f, indent=4)

            state_path = os.path.join(self.save_path, "states.json")
            state_dict = {
                "states": [],
                "internal_states": []
            }
            for page in self.currentGraph.page_nodes:
                for state in page.state_nodes:
                    state_dict["states"].append(state.to_dict())
            for internal_state in self.currentGraph.internal_state_nodes:
                state_dict["internal_states"].append(internal_state.to_dict())
            with open(state_path, "w") as f:
                json.dump(state_dict, f, indent=4)

            event_path = os.path.join(self.save_path, "events.json")
            event_dict = {
                "all_events": [],
                "mock_strategy_hash_map": MockStrategy.hash_map_to_dict()
            }
            for page in self.currentGraph.page_nodes:
                for state in page.state_nodes:
                    for event, target_node in state.transitions.items():
                        event_dict["all_events"].append(event.to_dict())
                    for event in state.available_events:
                        event_dict["all_events"].append(event.to_dict())

            for internal_state in self.currentGraph.internal_state_nodes:
                for event, target_node in internal_state.transitions.items():
                    event_dict["all_events"].append(event.to_dict())

            # Remove duplicate events by event.id, not the whole event object
            event_dict["all_events"] = list({event["event_id"]: event for event in event_dict["all_events"]}.values())
            # Sort the events by event_id
            event_dict["all_events"] = sorted(event_dict["all_events"], key=lambda x: x["event_id"])

            with open(event_path, "w") as f:
                json.dump(event_dict, f, indent=4)

            return True
        except Exception as e:
            print(f"Save Graph Error: {e}")
            return False

    def load_graph_from_file(self):
        """
        Load the graph from a file.
        :return: Boolean, whether the graph is loaded successfully.
        """
        from transition_graph.nodes.state_node import InternalStateNode, AbstractStateNode

        def _load_events(events_dict):
            from transition_graph.events.event import ClickEvent, TextInputEvent, BackEvent, InternalEvent, TextClearEvent, AbstractEvent
            # Load the events
            events = []
            max_id = 0
            MockStrategy.hash_map_from_dict(events_dict["mock_strategy_hash_map"])

            for event_dict in events_dict["all_events"]:
                event = None
                if event_dict["event_type"] == "click":
                    event = ClickEvent(None, event_dict["xpath"], (event_dict["position_x"], event_dict["position_y"]) if event_dict["position_x"] is not None else None)
                elif event_dict["event_type"] == "text_input":
                    event = TextInputEvent(None, event_dict["xpath"], MockStrategy.from_dict(event_dict["mock_strategy"]) if event_dict["mock_strategy"] is not None else None, event_dict["text"] if event_dict["text"] is not None else None)
                elif event_dict["event_type"] == "back":
                    event = BackEvent(None)
                elif event_dict["event_type"] == "text_clear":
                    event = TextClearEvent(None, event_dict["xpath"])
                elif event_dict["event_type"] == "internal":
                    event = InternalEvent(None)
                else:
                    print(f"Unknown event type: {event_dict['event_type']}")
                    raise ValueError

                event.event_id = event_dict["event_id"]
                max_id = max(max_id, event.event_id + 1)
                events.append(event)

            AbstractEvent.counter = max_id
            return events

        def _load_states(states_dict):
            from transition_graph.nodes.state_node import StateNode, InternalStateNode
            from device_infrastructure.actions import Screenshot
            # Load the states
            states = []
            max_id = 0
            max_screenshot_id = 0
            for state_dict in states_dict["states"]:
                state = StateNode(state_dict["name"], state_dict["component_tree"], state_dict["screenshot_path"])
                state.id = state_dict["id"]
                state.available_events = []
                state.visited_events = []
                state.transitions = {}

                max_id = max(max_id, state.id + 1)
                # /Users/xingjunyang/Documents/GitHub/PathMuTeG/screenshots/3.png -> 3
                if state.screenshot_path is not None:
                    max_screenshot_id = max(max_screenshot_id, int(state.screenshot_path.split("/")[-1].split(".")[0]) + 1)
                states.append(state)

            for internal_state_dict in states_dict["internal_states"]:
                internal_state = InternalStateNode(internal_state_dict["name"])
                internal_state.id = internal_state_dict["id"]
                internal_state.transitions = {}

                max_id = max(max_id, internal_state.id + 1)
                states.append(internal_state)

            AbstractStateNode.counter = max_id
            Screenshot.count = max_screenshot_id
            return states

        def _bind_states_and_events(states, events, events_dict, states_dict):
            # bind state to event
            for event in events:
                event_id = event.event_id
                state_id = next(filter(lambda x: x["event_id"] == event_id, events_dict["all_events"]))["state_node_id"]
                state = next(filter(lambda x: x.id == state_id, states))
                event.state_node = state

            # bind event to state
            for state_dict in states_dict["states"]:
                state_id = state_dict["id"]
                state = next(filter(lambda x: x.id == state_id, states))
                for transition_dict in state_dict["transitions"]:
                    event_id = transition_dict["event"]["event_id"]
                    event = next(filter(lambda x: x.event_id == event_id, events))
                    target_state_id = transition_dict["target_state_node_id"]
                    target_state = next(filter(lambda x: x.id == target_state_id, states))
                    state.add_transition(event, target_state)

                for available_event_dict in state_dict["available_events"]:
                    event_id = available_event_dict["event_id"]
                    event = next(filter(lambda x: x.event_id == event_id, events))
                    state.available_events.append(event)

                for visited_event_dict in state_dict["visited_events"]:
                    event_id = visited_event_dict["event_id"]
                    event = next(filter(lambda x: x.event_id == event_id, events))
                    state.visited_events.append(event)

            for internal_state_dict in states_dict["internal_states"]:
                state_id = internal_state_dict["id"]
                state = next(filter(lambda x: x.id == state_id, states))
                for transition_dict in internal_state_dict["transitions"]:
                    event_id = transition_dict["event"]["event_id"]
                    event = next(filter(lambda x: x.event_id == event_id, events))
                    target_state_id = transition_dict["target_state_node_id"]
                    target_state = next(filter(lambda x: x.id == target_state_id, states))
                    state.add_transition(event, target_state)

        def _load_page(pages_dict, states):
            pages = []
            max_id = 0
            for page_dict in pages_dict:
                page = PageNode(page_dict["name"], page_dict["current_activity"])
                page.id = page_dict["id"]
                page.state_nodes = []
                for state_node_dict in page_dict["state_nodes"]:
                    state_node_id = state_node_dict["id"]
                    state_node = next(filter(lambda x: x.id == state_node_id, states))
                    page.state_nodes.append(state_node)
                    state_node.parent_page_node = page
                max_id = max(max_id, page.id + 1)
                pages.append(page)

            PageNode.counter = max_id
            return pages


        # Use json to load the graph
        try:
            path = os.path.join(self.save_path, "graph.json")
            with open(path, "r") as f:
                graph_dict = json.load(f)

            state_path = os.path.join(self.save_path, "states.json")
            with open(state_path, "r") as f:
                states_dict = json.load(f)

            event_path = os.path.join(self.save_path, "events.json")
            with open(event_path, "r") as f:
                events_dict = json.load(f)

            # Load the states
            states = _load_states(states_dict)
            # Load the events
            events = _load_events(events_dict)
            # Bind states and events
            _bind_states_and_events(states, events, events_dict, states_dict)
            # Load the pages
            pages = _load_page(graph_dict["page_nodes"], states)

            # Build the graph
            self.currentGraph.start_page = next(filter(lambda x: x.id == graph_dict["start_page"]["id"], pages))
            self.currentGraph.start_state = next(filter(lambda x: x.id == graph_dict["start_state"]["id"], states))
            self.currentGraph.end_page = next(filter(lambda x: x.id == graph_dict["end_page"]["id"], pages))
            self.currentGraph.end_state = next(filter(lambda x: x.id == graph_dict["end_state"]["id"], states))
            self.currentGraph.page_nodes = pages
            self.currentGraph.internal_state_nodes = list(filter(lambda x: isinstance(x, InternalStateNode), states))

            return True

        except Exception as e:
            print(f"Load Graph Error: {e}")
            return False

    def calculate_exploration_coverage(self):
        """
        Calculate the exploration coverage of the graph.
        :return: The coverage percentage.
        """
        total_events = 0
        visited_events = 0

        for page in self.currentGraph.page_nodes:
            for state in page.state_nodes:
                total_events += len(state.available_events)
                visited_events += len(state.visited_events)

        if total_events == 0:
            return 0.0

        return (visited_events / total_events) * 100

    def calculate_states_count(self):
        states = []
        for page in self.currentGraph.page_nodes:
            for state in page.state_nodes:
                states.append(state)
        for internal_state in self.currentGraph.internal_state_nodes:
            states.append(internal_state)

        return len(states)

    def calculate_events_count(self):
        events = []
        for page in self.currentGraph.page_nodes:
            for state in page.state_nodes:
                for event, target_node in state.transitions.items():
                    events.append(event.to_dict())
                for event in state.available_events:
                    events.append(event.to_dict())
        for internal_state in self.currentGraph.internal_state_nodes:
            for event, target_node in internal_state.transitions.items():
                events.append(event.to_dict())
        events = list({event["event_id"]: event for event in events}.values())

        return len(events)

    def calculate_transitions_count(self):
        transition_count = 0
        for page in self.currentGraph.page_nodes:
            for state_node in page.state_nodes:
                transition_count += len(state_node.transitions)

        return transition_count


if __name__ == "__main__":
    from transition_graph.nodes.state_node import StateNode, AbstractStateNode
    from transition_graph.events.event import ClickEvent, TextInputEvent, AbstractEvent, TextClearEvent

    gm = GraphManager("/Users/xingjunyang/Documents/GitHub/PathMuTeG/config.yaml")
    pg1 = PageNode("page_1", {"key": "value"})
    gm.currentGraph.add_page_node(pg1)
    st1 = StateNode("state_1", "<xml>...</xml>", "screenshot_path")
    pg1.add_state_node(st1)
    st1.parent_page_node = pg1
    gm.set_start_state(st1)


    st2 = StateNode("state_2", "<xml>...</xml>", "screenshot_path")
    clk1 = ClickEvent(st1, "xpath")
    st1.add_transition(clk1, st2)
    pg2 = PageNode("page_2", {"key": "value"})
    gm.currentGraph.add_page_node(pg2)
    pg2.add_state_node(st2)
    st2.parent_page_node = pg2

    st3 = StateNode("state_3", "<xml>...</xml>", "screenshot_path")
    st2.add_transition(TextInputEvent(st2, "xpath", MockStrategy("letter", 10)), st3)
    pg2.add_state_node(st3)
    st3.parent_page_node = pg2

    gm.add_transition(clk1, st1, st3)

    st4 = StateNode("state_4", "<xml>...</xml>", "screenshot_path")
    pg1.add_state_node(st4)
    st4.parent_page_node = pg1
    gm.add_transition(clk1, st1, st4)

    gm.save_graph_to_file()

    gm2 = GraphManager("/Users/xingjunyang/Documents/GitHub/PathMuTeG/config2.yaml")
    gm2.load_graph_from_file()
    gm2.save_graph_to_file()



