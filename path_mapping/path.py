class Path:
    def __init__(self, start_path_node = None, path_array = None):
        if path_array is not None:
            self.from_array(path_array)
            return

        if start_path_node is None:
            self.start_path_node = None
            self.end_path_node = None
        else:
            self.start_path_node = start_path_node
            self.end_path_node = start_path_node

    def add_path_node(self, path_node):
        if self.start_path_node is None:
            self.start_path_node = path_node
            self.end_path_node = path_node
        else:
            self.end_path_node.next_path_node = path_node
            self.end_path_node = path_node

    def to_array(self):
        from path_mapping.path_node import InternalPathNode, PathNode

        path_array = []
        current_node = self.start_path_node
        while current_node is not None:
            if isinstance(current_node, InternalPathNode):
                new_path_node = InternalPathNode(current_node.state, current_node.event)
            else:
                new_path_node = PathNode(current_node.state, current_node.event)
            path_array.append(new_path_node)
            current_node = current_node.next_path_node
        return path_array

    def from_array(self, path_array):
        if len(path_array) == 0:
            return
        from path_mapping.path_node import PathNode, InternalPathNode

        if isinstance(path_array[0], PathNode):
            self.start_path_node = PathNode(path_array[0].state, path_array[0].event)
        else:
            self.start_path_node = InternalPathNode(path_array[0].state, path_array[0].event)
        self.end_path_node = self.start_path_node

        for i in range(1, len(path_array)):
            if isinstance(path_array[i], PathNode):
                new_path_node = PathNode(path_array[i].state, path_array[i].event)
            else:
                new_path_node = InternalPathNode(path_array[i].state, path_array[i].event)
            self.end_path_node.next_path_node = new_path_node
            self.end_path_node = new_path_node