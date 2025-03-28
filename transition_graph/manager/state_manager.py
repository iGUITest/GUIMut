from device_infrastructure import DeviceManager
from transition_graph.nodes.state_node import StateNode


class StateManager:
    def __init__(self, device_mng: DeviceManager):
        self.device_mng = device_mng

    def capture_new_state(self) -> StateNode:
        """
        Capture a new state from the current activity.
        :return: The new state node.
        """
        component_tree = self.device_mng.get_component_tree()
        screenshot_path = self.device_mng.take_screenshot()

        state_node = StateNode("state_node", component_tree, screenshot_path)
        return state_node

    def capture_current_activity(self) -> dict:
        """
        Capture the current activity.
        :return: The current activity.
        """
        return self.device_mng.get_current_activity()