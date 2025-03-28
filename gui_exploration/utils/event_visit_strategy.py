class AbstractEventVisitStrategy:
    """
    A class to handle visit events strategy for GUI exploration.
    """

    def choose_event(self, visited_events, unvisited_events, transitions=None):
        """
        Choose an event to visit based on the strategy.

        :param visited_events: List of visited events.
        :param unvisited_events: List of unvisited events.
        :return: The chosen event.
        """
        raise NotImplementedError("This method should be overridden by subclasses.")

class UnvisitedPriorEventVisitStrategy(AbstractEventVisitStrategy):
    """
    A class to handle random visit events strategy for GUI exploration.
    """

    def choose_event(self, visited_events, unvisited_events, transitions=None):
        """
        Choose a random event to visit from the unvisited events.

        :param visited_events: List of visited events.
        :param unvisited_events: List of unvisited events.
        :return: A randomly chosen event from the unvisited events.
        """
        import random
        if not unvisited_events:
            return random.choice(visited_events)
        return random.choice(unvisited_events)

class RandomEventVisitStrategy(AbstractEventVisitStrategy):
    """
    A class to handle random visit events strategy for GUI exploration.
    """
    def __init__(self, visited_events_weight):
        """
        Initialize the RandomEventVisitStrategy with a weight for visited events.

        :param visited_events_weight: Weight for visited events.
        """
        self.visited_events_weight = visited_events_weight

    def choose_event(self, visited_events, unvisited_events, transitions=None):
        """
        Choose a random event to visit from the unvisited events.

        :param visited_events: List of visited events.
        :param unvisited_events: List of unvisited events.
        :return: A randomly chosen event from the unvisited events.
        """
        import random
        if not unvisited_events:
            return random.choice(visited_events)
        # Choose a random event from unvisited events and visited events, with a bias towards unvisited events
        all_events = unvisited_events + visited_events
        weights = [1] * len(unvisited_events) + [self.visited_events_weight] * len(visited_events)
        return random.choices(all_events, weights=weights)[0]

class SequentialEventVisitStrategy(AbstractEventVisitStrategy):
    """
    A class to handle sequential visit events strategy for GUI exploration.
    """

    def choose_event(self, visited_events, unvisited_events, transitions=None):
        """
        Choose the first unvisited event from the unvisited events.

        :param visited_events: List of visited events.
        :param unvisited_events: List of unvisited events.
        :return: The first unvisited event.
        """
        if not unvisited_events:
            return visited_events[0]
        return unvisited_events[0]

class GraphOptimizedEventVisitStrategy(AbstractEventVisitStrategy):
    """
    A class to handle graph-optimized visit events strategy for GUI exploration.
    This strategy uses the graph structure to determine the best event to visit next.
    """

    def __init__(self, graph_manager):
        """
        Initialize the GraphOptimizedEventVisitStrategy with a graph manager.

        :param graph_manager: The graph manager instance.
        """
        self.graph_manager = graph_manager

    def choose_event(self, visited_events, unvisited_events, transitions=None):
        """
        Choose an event based on the graph structure and coverage.

        If we have unvisited events, we will choose one of them randomly.
        If we have no unvisited events, we will choose the best event based on the graph structure and coverage.

        :param transitions: List of transitions of the Node.
        :param visited_events: List of visited events.
        :param unvisited_events: List of unvisited events.
        :return: An event chosen based on the graph structure and coverage.
        """
        import random
        from transition_graph.nodes.state_node import StateNode, InternalStateNode

        # Have unvisited events, choose one of them randomly
        if unvisited_events:
            return random.choice(unvisited_events)

        # No unvisited events, choose the best event based on BFS (select the event with the most unvisited children)
        exploration_queue = []
        visited_state_nodes = set()
        reachable_nodes = {key: set() for key in visited_events}
        event_coverage = {key: 0 for key in visited_events}

        for event in visited_events:
            state_node = transitions[event]
            level = 1
            if isinstance(state_node, StateNode):
                exploration_queue.append((state_node, event, level))
            elif isinstance(state_node, InternalStateNode):
                # If the state node is an internal state node, we need to explore its transitions
                for internal_event in state_node.transitions:
                    exploration_queue.append((state_node.transitions[internal_event], event, level))

        while exploration_queue:
            current_node, event, level = exploration_queue.pop(0)
            reachable_nodes[event].add((current_node, level))
            if current_node in visited_state_nodes:
                continue
            visited_state_nodes.add(current_node)
            for next_event in current_node.transitions:
                next_node = current_node.transitions[next_event]
                if isinstance(next_node, StateNode):
                    exploration_queue.append((next_node, event, level + 1))
                elif isinstance(next_node, InternalStateNode):
                    # If the state node is an internal state node, we need to explore its transitions
                    for internal_event in next_node.transitions:
                        exploration_queue.append((next_node.transitions[internal_event], event, level + 1))

        # calculate the coverage of each event
        for event in visited_events:
            coverages = []
            result = 0

            for node, level in reachable_nodes[event]:
                if (len(node.get_unvisited_events()) + len(node.get_visited_events())) == 0:
                    coverages.append(1.0)
                    continue
                page_states_count = len(node.parent_page_node.state_nodes)
                events_count = len(node.get_unvisited_events()) + len(node.get_visited_events())
                unvisited_rate = (len(node.get_unvisited_events()) / events_count)
                coverage = 1.0 - unvisited_rate * (1 / level) * (min(1.0, (5 / page_states_count))) * (min(1.0, (10 / events_count)))
                coverages.append(coverage)

            for coverage in coverages:
                result += coverage
            event_coverage[event] = result / len(coverages) if coverages else 1

        # Choose the event with the lowest coverage. If there are multiple events with the same coverage, choose one randomly.
        lowest_coverage = float("inf")
        best_events = []
        for event, coverage in event_coverage.items():
            if coverage < lowest_coverage:
                lowest_coverage = coverage
                best_events = [event]
            elif coverage == lowest_coverage:
                best_events.append(event)

        for event in visited_events:
            print(f"Event: {event}, Coverage: {event_coverage[event]}")

        print(f"Best events: {best_events}")

        return random.choice(best_events) if best_events else None