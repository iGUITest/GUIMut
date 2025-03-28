from mutator.find_checkpoint import AbstractFindCheckpointStrategy

class AbstractMetamorphicRelation:
    """
    Abstract class for defining metamorphic relations.
    """

    from transition_graph.nodes.transition_graph_node import TransitionGraphNode
    from path_mapping import Path
    def __init__(self, find_checkpoint_strategy: AbstractFindCheckpointStrategy, max_mutations: int, max_path_length: int):
        """
        Initialize the metamorphic relation with maximum mutations and path length.
        """
        self.max_mutations = max_mutations
        self.max_path_length = max_path_length
        self.find_checkpoint_strategy = find_checkpoint_strategy

    def mutate(self, path: Path, graph: TransitionGraphNode) -> list[Path]:
        """
        Mutate the input data according to the metamorphic relation.
        """
        raise NotImplementedError("Subclasses should implement this method.")


class MRReplace(AbstractMetamorphicRelation):
    """
    Metamorphic relation for replacing sequences in a path. Ensuring the first and last nodes of the sequence remain unchanged.
    Modified to allow replacement of segments with just 2 nodes.
    """

    from transition_graph.nodes.transition_graph_node import TransitionGraphNode
    from path_mapping import Path

    def __init__(self, find_checkpoint_strategy, max_mutations: int = 10, max_path_length: int = 10):
        super(MRReplace, self).__init__(find_checkpoint_strategy, max_mutations, max_path_length)

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

        checkpoints = self.find_checkpoint_strategy.find_checkpoint_in_path(path, graph)

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
    def __init__(self, find_checkpoint_strategy, max_mutations: int = 10, max_path_length: int = 10):
        super(MRCycle, self).__init__(find_checkpoint_strategy, max_mutations, max_path_length)

    def mutate(self, path: Path, graph: TransitionGraphNode) -> list[Path]:
        """
        Insert cycles at non-checkpoint states in the path.
        """
        from path_mapping.path_node import InternalPathNode, PathNode
        from path_mapping.path import Path

        path_array = path.to_array()
        if len(path_array) < 3: # Need at least 3 nodes to have a replaceable segment
            return [path]
        
        checkpoints = self.find_checkpoint_strategy.find_checkpoint_in_path(path, graph)

        mutated_paths = []

        for i in range(len(path_array)):
            current_node = path_array[i]

            # skip checkpoints
            if i in checkpoints:
                continue

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
            for event in current_state.transitions.keys():
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