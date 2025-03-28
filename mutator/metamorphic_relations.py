class AbstractMetamorphicRelation:
    """
    Abstract class for defining metamorphic relations.
    """

    from transition_graph.nodes.transition_graph_node import TransitionGraphNode
    from path_mapping import Path
    def __init__(self, max_mutations: int = 10, max_path_length: int = 10):
        """
        Initialize the metamorphic relation with maximum mutations and path length.
        """
        self.max_mutations = max_mutations
        self.max_path_length = max_path_length

    def mutate(self, path: Path, graph: TransitionGraphNode) -> list[Path]:
        """
        Mutate the input data according to the metamorphic relation.
        """
        raise NotImplementedError("Subclasses should implement this method.")


class MRPlainPath(AbstractMetamorphicRelation):
    """
    Metamorphic relation for plain path.
    """

    from transition_graph.nodes.transition_graph_node import TransitionGraphNode
    from path_mapping import Path
    def __init__(self, max_mutations: int = 10, max_path_length: int = 10):
        super(MRPlainPath, self).__init__(max_mutations, max_path_length)

    def mutate(self, path: Path, graph: TransitionGraphNode) -> list[Path]:
        from path_mapping.path_node import InternalPathNode
        from path_mapping.path import Path

        path_array = path.to_array()

        mutable_paths = []
        # find two non-internal path nodes as the start and end of the path
        for i in range(len(path_array)):
            for j in range(i + 1, len(path_array)):
                if isinstance(path_array[i], InternalPathNode) or isinstance(path_array[j], InternalPathNode):
                    continue
                mutable_paths.append(path_array[i : j + 1])

        mutates = [] # list of mutated paths
        paths = [] # mutated path_arrays

        batch_size = 5

        for mutable_path in mutable_paths:
            path_length_step = (self.max_path_length - len(mutable_path)) // (self.max_mutations // batch_size)
            for i in range(len(mutable_path), self.max_path_length, path_length_step):
                # gradually increase max_path_length
                new_paths = self.__mutate_path_by_path_array(mutable_path, batch_size, i, previous_paths=paths)
                prefix_part = path_array[:path_array.index(mutable_path[0])]
                suffix_part = path_array[path_array.index(mutable_path[-1]):]
                for new_path in new_paths:
                    new_complete_path = []
                    new_complete_path.extend(prefix_part)
                    new_complete_path.extend(new_path)
                    new_complete_path.extend(suffix_part)
                    paths.append(new_complete_path)

        for path in paths:
            if len(path) <= self.max_path_length:
                new_path = Path(path_array=path)
                mutates.append(new_path)

        return mutates

    def __mutate_path_by_path_array(self, path_array, max_mutations, max_path_length, previous_paths=None):
        """
        Generate a new path by mutating the given path array.
        The first node and the last node should be the same as the original path.
        No internal path node should be generated in the new path.
        The new path should be valid, i.e., each node should be reachable from the previous node.
        :param path_array: The path array to be mutated.
        :param max_mutations: The maximum number of mutations allowed.
        :param max_path_length: The maximum path length allowed.
        :return: A new path array.
        """
        from transition_graph.nodes.state_node import InternalStateNode
        from path_mapping.path_node import PathNode
        from collections import deque, defaultdict

        if len(path_array) < 2:
            return []

        paths = []
        start = path_array[0]
        end = path_array[-1]

        reverse_graph = defaultdict(list)
        all_nodes = set()

        # Build the graph structure by exploring from start
        def build_graph():
            queue = deque([start.state])
            visited = set([start.state])

            while queue:
                node = queue.popleft()
                all_nodes.add(node)

                for event in node.transitions:
                    next_node = node.transitions[event]
                    # Add the reverse edge

                    reverse_graph[next_node].append((node, event))

                    if next_node not in visited:
                        visited.add(next_node)
                        queue.append(next_node)

        build_graph()

        min_distances = {node: float('inf') for node in all_nodes}
        min_distances[end.state] = 0

        def calculate_min_distances():
            queue = deque([end.state])

            while queue:
                node = queue.popleft()

                # Process all predecessors
                for pred_node, event in reverse_graph[node]:
                    if min_distances[pred_node] > min_distances[node] + 1:
                        min_distances[pred_node] = min_distances[node] + 1
                        queue.append(pred_node)

        calculate_min_distances()

        def backtrack(node, path, path_nodes):
            # Stop if we've found enough paths
            if len(paths) >= max_mutations:
                return

            # Check if we've reached the end
            if node == end.state and len(path_nodes) >= 1:
                # Check if this path is already found
                is_duplicate = False

                existing_paths = paths
                if previous_paths is not None:
                    existing_paths = existing_paths.copy() + previous_paths
                for p in existing_paths:
                    if len(p) == len(path_nodes) and all(x.state == y.state and x.event == y.event for x, y in zip(p, path_nodes)):
                        is_duplicate = True
                        break

                if not is_duplicate:
                    paths.append(path_nodes.copy())
                return

            # Stop if we've exceeded max path length
            if len(path) >= max_path_length:
                return

            # Skip internal state nodes
            if isinstance(node, InternalStateNode):
                return

            # Check if we have enough budget to reach the end
            remaining_steps = max_path_length - len(path)
            if min_distances[node] > remaining_steps:
                return

            for event in node.visited_events:
                next_node = node.transitions[event]
                path.append(next_node)
                path_nodes.append(PathNode(node, event))
                backtrack(next_node, path, path_nodes)
                path.pop()
                path_nodes.pop()


        backtrack(start.state, [start.state], [])
        return paths


class MREnvironment(AbstractMetamorphicRelation):
    """
    Metamorphic relation for environment.
    """

    from transition_graph.nodes.transition_graph_node import TransitionGraphNode
    from path_mapping import Path
    def __init__(self, max_mutations: int = 10, max_path_length: int = 10, config: dict = None):
        super(MREnvironment, self).__init__(max_mutations, max_path_length)
        self.config = config

    def mutate(self, path: Path, graph: TransitionGraphNode) -> list[Path]:
        """
        TODO: Implement the mutation logic for plain path. For now, return the original path
        """

        return [path]


class MRReplace(AbstractMetamorphicRelation):
    """
    Metamorphic relation for replacing sequences in a path. Ensuring the first and last nodes of the sequence remain unchanged.
    Modified to allow replacement of segments with just 2 nodes.
    """

    from transition_graph.nodes.transition_graph_node import TransitionGraphNode
    from path_mapping import Path

    def __init__(self, max_mutations: int = 10, max_path_length: int = 10):
        super(MRReplace, self).__init__(max_mutations, max_path_length)

    def mutate(self, path: Path, graph: TransitionGraphNode) -> list[Path]:
        """
        Replace path segments between checkpoints with alternative paths.
        Checkpoints are preserved and their order remains consistent.
        Now allows replacement of segments with just 2 nodes.
        """
        from path_mapping.path_node import InternalPathNode
        from path_mapping.path import Path

        path_array = path.to_array()
        if len(path_array) < 2:  # need at least 2 nodes to have a replaceable segment
            return [path]

        checkpoints = set()
        checkpoints.add(0)
        checkpoints.add(len(path_array) - 1)

        mutated_paths = []

        # find all possible segments between checkpoints that can be replaced
        checkpoint_indices = sorted(list(checkpoints))

        for i in range(len(checkpoint_indices) - 1):
            start_idx = checkpoint_indices[i]
            end_idx = checkpoint_indices[i + 1]

            if end_idx - start_idx < 1:
                continue

            for s in range(start_idx, end_idx):
                for e in range(s + 1, end_idx + 1):
                    # start node can be internal node, while end node can't
                    can_replace = True
                    if isinstance(path_array[e], InternalPathNode):
                        can_replace = False

                    if not can_replace:
                        continue

                    # generate alternative paths between start and end checkpoints
                    start_node = path_array[s]
                    end_node = path_array[e]

                    alternative_segments = self._find_alternative_paths(
                        start_node.state, end_node.state,
                        self.max_path_length - len(path_array) + (e - s),
                        path_array[s:e + 1]  # original segment to avoid
                    )

                    # create mutated paths by replacing the segment
                    for alt_segment in alternative_segments:
                        if len(mutated_paths) >= self.max_mutations:
                            break

                        new_path_array = []
                        new_path_array.extend(path_array[:s])
                        new_path_array.extend(alt_segment[:-1])
                        new_path_array.extend(path_array[e:])

                        if len(new_path_array) <= self.max_path_length:
                            mutated_paths.append(Path(path_array=new_path_array))

            if len(mutated_paths) >= self.max_mutations:
                break

        return mutated_paths

    def _find_alternative_paths(self, start_state, end_state, max_length, original_segment):
        """
        Find alternative paths between start_state and end_state that are different from the original segment.
        """
        from path_mapping.path_node import PathNode, InternalPathNode
        from path_mapping.path import Path
        from transition_graph.nodes.state_node import StateNode
        from collections import deque

        if start_state == end_state:
            return []

        alternative_paths = []

        # BFS to find paths from start to end
        start_state_path_node = PathNode(start_state, None) if isinstance(start_state, StateNode) else InternalPathNode(start_state, None)
        queue = deque([(start_state, [start_state_path_node])])
        visited_paths = set()

        while queue and len(alternative_paths) < self.max_mutations:
            current_state, current_path = queue.popleft()

            if len(current_path) > max_length:
                continue

            if current_state == end_state and len(current_path) > 1:
                # Check if this path is different from the original segment
                if self._is_different_path(current_path, original_segment):
                    path_signature = tuple((node.state, node.event) for node in current_path)
                    if path_signature not in visited_paths:
                        visited_paths.add(path_signature)
                        alternative_paths.append(current_path)
                continue

            # Explore transitions
            for event, next_state in current_state.transitions.items():
                current_path[-1].event = event
                next_path_node = PathNode(next_state, None) if isinstance(next_state, StateNode) else InternalPathNode(next_state, None)
                new_path = Path(path_array=current_path).to_array() + [next_path_node] # Deep copy of current_path
                queue.append((next_state, new_path))

        return alternative_paths

    def _is_different_path(self, new_path, original_segment):
        """
        Check if the new path is significantly different from the original segment.
        """
        if len(new_path) != len(original_segment):
            return True

        for i in range(len(new_path)):
            if new_path[i].state != original_segment[i].state:
                return True

        return False


class MRCycle(AbstractMetamorphicRelation):
    """
    Metamorphic relation for replacing a node in a path with a cycle. The node is in the cycle.
    """

    from transition_graph.nodes.transition_graph_node import TransitionGraphNode
    from path_mapping import Path
    def __init__(self, max_mutations: int = 10, max_path_length: int = 10):
        super(MRCycle, self).__init__(max_mutations, max_path_length)

    def mutate(self, path: Path, graph: TransitionGraphNode) -> list[Path]:
        """
        Insert cycles at non-checkpoint states in the path.
        """
        from path_mapping.path_node import InternalPathNode, PathNode
        from path_mapping.path import Path

        path_array = path.to_array()
        if len(path_array) < 3: # Need at least 3 nodes to have a replaceable segment
            return [path]

        # first and last nodes are always checkpoints
        checkpoints = set()
        checkpoints.add(0)
        checkpoints.add(len(path_array) - 1)

        mutated_paths = []

        for i in range(len(path_array)):
            current_node = path_array[i]

            # skip internal path nodes
            if isinstance(current_node, InternalPathNode):
                continue

            cycles = self._find_cycles_at_state(current_node.state, self.max_path_length - len(path_array))

            # insert each cycle at this position
            for cycle in cycles:
                if len(mutated_paths) >= self.max_mutations:
                    break

                new_path_array = []
                new_path_array.extend(path_array[:i])
                new_path_array.extend(cycle)  # Insert the cycle
                new_path_array.extend(path_array[i:])  # Continue from next node

                if len(new_path_array) <= self.max_path_length:
                    mutated_paths.append(Path(path_array=new_path_array))

            if len(mutated_paths) >= self.max_mutations:
                break

        return mutated_paths

    def _find_cycles_at_state(self, state, max_cycle_length):
        """
        Find cycles that start and end at the given state.
        """
        from path_mapping.path_node import PathNode, InternalPathNode
        from path_mapping.path import Path
        from transition_graph.nodes.state_node import StateNode

        if max_cycle_length < 2:
            return []

        cycles = []

        # DFS to find cycles
        def dfs_find_cycles(current_state, path, visited_states, remaining_length):
            if len(cycles) >= self.max_mutations:
                return

            if remaining_length <= 0:
                return

            # Skip internal states in cycle detection
            # if isinstance(current_state, InternalStateNode):
            #     return

            if current_state == state and len(path) > 1:
                cycle_path = []
                for i in range(len(path) - 1):
                    event = self._get_event_between_states(path[i], path[i + 1])
                    new_path_node = PathNode(path[i], event) if isinstance(path[i], StateNode) else InternalPathNode(path[i], event)
                    cycle_path.append(new_path_node)

                if len(cycle_path) > 0:
                    cycles.append(cycle_path)
                return

            # avoid revisiting states
            if current_state in visited_states and current_state != state:
                return

            visited_states.add(current_state)

            # Explore transitions
            for event in getattr(current_state, 'visited_events', []):
                if event in current_state.transitions:
                    next_state = current_state.transitions[event]
                    new_path = path + [next_state] # deep clone of path array
                    dfs_find_cycles(next_state, new_path, visited_states.copy(), remaining_length - 1)

        # Start DFS from the given state
        dfs_find_cycles(state, [state], set(), max_cycle_length)

        return cycles

    def _get_event_between_states(self, from_state, to_state):
        """
        Find the event that transitions from from_state to to_state.
        """
        if hasattr(from_state, 'transitions'):
            for event, next_state in from_state.transitions.items():
                if next_state == to_state:
                    return event
        return None