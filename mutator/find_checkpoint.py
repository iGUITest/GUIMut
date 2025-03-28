import re
from collections import defaultdict
import xml.etree.ElementTree as ET

from path_mapping import Path
from transition_graph.nodes.transition_graph_node import TransitionGraphNode
from transition_graph.nodes.state_node import StateNode


class AbstractFindCheckpointStrategy:
    def find_candidate_checkpoints(self, graph: TransitionGraphNode):
        """Find checkpoint state nodes in the graph. Return the set of checkpoint state IDs.

        Returns:
            set[int]: state IDs of checkpoint nodes.
        """
        raise NotImplementedError()
    
    def find_checkpoint_in_path(self, path: Path, graph: TransitionGraphNode):
        """Determine which indices in a path are checkpoints.

        Always includes the first and last nodes. Additionally, any path node
        whose state ID matches a candidate checkpoint is also marked as a checkpoint.

        Returns:
            set[int]: indices in the path array that are checkpoints.
        """
        path_array = path.to_array()
        checkpoints_indices = set()

        # The first and last nodes are always checkpoints
        checkpoints_indices.add(0)
        if len(path_array) > 1:
            checkpoints_indices.add(len(path_array) - 1)

        # Find candidate checkpoints from graph-level heuristic analysis
        candidate_checkpoints = self.find_candidate_checkpoints(graph)

        # Match path nodes against candidate checkpoint state IDs
        for idx, path_node in enumerate(path_array):
            if hasattr(path_node, 'state') and path_node.state is not None:
                state_id = path_node.state.id
                if state_id in candidate_checkpoints:
                    checkpoints_indices.add(idx)

        return checkpoints_indices


class HeuristicFindCheckpointStrategy(AbstractFindCheckpointStrategy):
    # Weights for each heuristic rule
    WEIGHT_HIGH_INDEGREE = 3.0
    WEIGHT_CUT_VERTEX = 4.0
    WEIGHT_FORM_DIALOG = 2.0

    # Minimum total score to qualify as a candidate checkpoint
    CHECKPOINT_THRESHOLD = 4.0

    def _build_graph_adjacency(self, graph: TransitionGraphNode):
        """Build adjacency list (directed) and reverse adjacency for the FSM graph.

        Returns:
            adjacency: dict mapping source_state_id -> list of target_state_ids
            reverse_adjacency: dict mapping target_state_id -> list of source_state_ids
            all_state_ids: set of all state node IDs in the graph
        """
        adjacency = defaultdict(list)
        reverse_adjacency = defaultdict(list)
        all_state_ids = set()

        # Collect transitions from regular state nodes in page nodes
        for page_node in graph.page_nodes:
            for state_node in page_node.state_nodes:
                all_state_ids.add(state_node.id)
                for event, target_node in state_node.transitions.items():
                    adjacency[state_node.id].append(target_node.id)
                    reverse_adjacency[target_node.id].append(state_node.id)
                    all_state_ids.add(target_node.id)

        # Collect transitions from internal state nodes
        for internal_node in graph.internal_state_nodes:
            all_state_ids.add(internal_node.id)
            for event, target_node in internal_node.transitions.items():
                adjacency[internal_node.id].append(target_node.id)
                reverse_adjacency[target_node.id].append(internal_node.id)
                all_state_ids.add(target_node.id)

        return adjacency, reverse_adjacency, all_state_ids


    def _build_undirected_adjacency(self, adjacency):
        """Convert directed adjacency to undirected for cut-vertex analysis."""
        undirected = defaultdict(set)
        for src, targets in adjacency.items():
            for tgt in targets:
                undirected[src].add(tgt)
                undirected[tgt].add(src)
        return undirected


    def _compute_indegrees(self, reverse_adjacency):
        """Compute in-degree for each node from the reverse adjacency."""
        indegrees = {}
        for target_id, source_ids in reverse_adjacency.items():
            indegrees[target_id] = len(source_ids)
        return indegrees


    def _find_cut_vertices(self, undirected_adj, all_state_ids):
        """Find articulation points (cut vertices) using Tarjan's algorithm.

        An articulation point is a node whose removal increases the number of
        connected components in the graph. Uses DFS on the undirected graph.
        """
        visited = set()
        disc = {}       # discovery time
        low = {}        # lowest discovery time reachable
        parent = {}     # parent in DFS tree
        ap = set()      # articulation points
        time = [0]

        def dfs(u):
            children = 0
            visited.add(u)
            disc[u] = time[0]
            low[u] = time[0]
            time[0] += 1

            for v in undirected_adj.get(u, set()):
                if v not in visited:
                    children += 1
                    parent[v] = u
                    dfs(v)
                    low[u] = min(low[u], low[v])
                    # Non-root: u is AP if low[v] >= disc[u]
                    if u in parent and low[v] >= disc[u]:
                        ap.add(u)
                elif v != parent.get(u):
                    low[u] = min(low[u], disc[v])

            # Root is AP if it has more than one child in DFS tree
            if u not in parent and children > 1:
                ap.add(u)

        for node_id in all_state_ids:
            if node_id not in visited:
                # Only run DFS from nodes that have neighbors
                if node_id in undirected_adj:
                    dfs(node_id)

        return ap


    def _has_form_or_dialog(self, state_node: StateNode):
        """Check if a state node contains form submission or dialog elements.

        Analyzes the component_tree XML of the state node for:
        - Form-related widgets (EditText, CheckBox, RadioButton, Spinner, etc.)
        - Dialog/confirmation indicators (resource-id patterns like 'ok', 'confirm',
        'submit', 'alert', 'dialog', etc.)
        - A state qualifies if it has >= 2 distinct form element types OR any dialog indicators.
        """
        if not hasattr(state_node, 'component_tree') or not state_node.component_tree:
            return False

        try:
            root = ET.fromstring(state_node.component_tree)
        except ET.ParseError:
            return False

        # Android widget class names that indicate form-like UIs
        form_widget_classes = {
            'EditText', 'AutoCompleteTextView', 'MultiAutoCompleteTextView',
            'CheckBox', 'RadioButton', 'Switch', 'ToggleButton',
            'RatingBar', 'SeekBar', 'Spinner',
            'DatePicker', 'TimePicker', 'NumberPicker',
            'AlertDialog', 'Dialog',
            'CalendarView',
        }

        # Resource-id / text patterns suggesting dialog or confirmation
        dialog_patterns = [
            r'\bok\b', r'\bcancel\b', r'\bconfirm\b', r'\bsubmit\b',
            r'\bsave\b', r'\bdelete\b', r'\byes\b', r'\bno\b',
            r'\balert\b', r'\bdialog\b', r'\bpopup\b', r'\bpermission\b',
            r'\ballow\b', r'\bdeny\b', r'\bagree\b', r'\bdisagree\b',
            r'\bcontinue\b', r'\bdismiss\b',
        ]

        found_form_classes = set()
        found_dialog_indicators = 0

        def scan_element(element):
            nonlocal found_form_classes, found_dialog_indicators

            class_name = element.attrib.get('class', '')
            # Check for form widget classes
            for widget in form_widget_classes:
                if widget in class_name:
                    found_form_classes.add(widget)

            # Check resource-id for dialog/confirmation patterns
            resource_id = element.attrib.get('resource-id', '').lower()
            text = element.attrib.get('text', '').lower()
            content_desc = element.attrib.get('content-desc', '').lower()
            combined_text = f"{text} {content_desc}"

            for pattern in dialog_patterns:
                if re.search(pattern, resource_id) or re.search(pattern, combined_text):
                    found_dialog_indicators += 1
                    break  # count each element at most once

            for child in element:
                scan_element(child)

        scan_element(root)

        return len(found_form_classes) >= 2 or found_dialog_indicators >= 1


    def _get_state_by_id(self, graph: TransitionGraphNode, state_id: int):
        """Look up a state node in the graph by its ID."""
        for page_node in graph.page_nodes:
            for state_node in page_node.state_nodes:
                if state_node.id == state_id:
                    return state_node
        for internal_node in graph.internal_state_nodes:
            if internal_node.id == state_id:
                return internal_node
        return None


    def find_candidate_checkpoints(self, graph: TransitionGraphNode):
        """Analyze the FSM graph and return a set of state IDs qualifying as checkpoints.

        Applies three heuristic rules with weighted scoring:
        1. High in-degree nodes — states that are reached from many different
            source states are likely important junctions.
        2. Cut vertices (articulation points) — removing such a node disconnects
            the graph, making it a critical waypoint.
        3. Form / dialog states — states containing form fields, confirmation
            dialogs, or similar important UI patterns.

        Each rule contributes to a weighted score. States whose total score meets
        CHECKPOINT_THRESHOLD are returned as candidate checkpoints.
        """
        adjacency, reverse_adjacency, all_state_ids = self._build_graph_adjacency(graph)
        indegrees = self._compute_indegrees(reverse_adjacency)

        undirected_adj = self._build_undirected_adjacency(adjacency)
        cut_vertices = self._find_cut_vertices(undirected_adj, all_state_ids)

        # Determine high in-degree threshold: use median, with a floor of 2
        indegree_values = [indegrees.get(nid, 0) for nid in all_state_ids
                        if nid in adjacency or nid in reverse_adjacency]
        if indegree_values:
            sorted_vals = sorted(indegree_values)
            median_indegree = sorted_vals[len(sorted_vals) // 2]
        else:
            median_indegree = 1
        high_indegree_threshold = max(median_indegree, 2)

        candidate_scores = defaultdict(float)

        for state_id in all_state_ids:
            score = 0.0

            # Rule 1: High in-degree
            indeg = indegrees.get(state_id, 0)
            if indeg > high_indegree_threshold:
                score += self.WEIGHT_HIGH_INDEGREE * (indeg / high_indegree_threshold)

            # Rule 2: Cut vertex (articulation point)
            if state_id in cut_vertices:
                score += self.WEIGHT_CUT_VERTEX

            # Rule 3: Form / dialog content
            state_node = self._get_state_by_id(graph, state_id)
            if state_node is not None and isinstance(state_node, StateNode):
                if self._has_form_or_dialog(state_node):
                    score += self.WEIGHT_FORM_DIALOG

            if score >= self.CHECKPOINT_THRESHOLD:
                candidate_scores[state_id] = score

        return set(candidate_scores.keys())


class ManualFindCheckpointStrategy(AbstractFindCheckpointStrategy):
    def find_candidate_checkpoints(self, graph: TransitionGraphNode):
        """Find state nodes in the graph that have the 'custom_checkpoint' flag set.

        Iterates through all state nodes in the graph and collects the IDs of those
        marked as custom checkpoints.

        Returns:
            set[int]: state IDs of nodes where custom_checkpoint is True.
        """
        candidate_ids = set()

        for page_node in graph.page_nodes:
            for state_node in page_node.state_nodes:
                if hasattr(state_node, 'custom_checkpoint') and state_node.custom_checkpoint:
                    candidate_ids.add(state_node.id)

        return candidate_ids