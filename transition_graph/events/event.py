from device_infrastructure import DeviceManager

from transition_graph.utils.mock_strategy import MockStrategy


class AbstractEvent:
    counter = 0

    def __init__(self, state_node):
        self.state_node = state_node # indicates the state node that the event belongs to
        self.event_id = AbstractEvent.counter
        AbstractEvent.counter += 1

    def perform(self, device_mng: DeviceManager):
        raise NotImplementedError

    def to_dict(self) -> dict:
        raise NotImplementedError

class ClickEvent(AbstractEvent):
    from transition_graph.nodes.state_node import StateNode

    def __init__(self, state_node, xpath, position=None):
        """
        Create a click event
        :param state_node: the state node that the event belongs to
        :param xpath: the xpath of the element to be clicked
        :param position: the position of the element to be clicked. If not provided, the xpath will be used to locate the element. Otherwise, the position will be used.
        """
        super(ClickEvent, self).__init__(state_node)
        self.xpath = xpath
        if position is not None:
            self.position_x, self.position_y = position
        else:
            self.position_x = None
            self.position_y = None

    def __str__(self):
        return f"ClickEvent event_{self.event_id} on state_node_{self.state_node.id}: (Xpath: {self.xpath}, Position: ({self.position_x}, {self.position_y}))"

    def perform(self, device_mng: DeviceManager):
        if self.position_x is None or self.position_y is None:
            # locate the element by xpath
            device_mng.click_by_xpath(self.xpath)
        else:
            device_mng.click_by_coordinate(self.position_x, self.position_y)

    def to_dict(self) -> dict:
        return {
            "state_node_id": self.state_node.id,
            "event_id": self.event_id,
            "event_type": "click",
            "xpath": self.xpath,
            "position_x": self.position_x,
            "position_y": self.position_y
        }

class TextInputEvent(AbstractEvent):
    from transition_graph.utils.mock_strategy import MockStrategy

    def __init__(self, state_node, xpath, mock_strategy: MockStrategy, text=None):
        """
        Create a text input event
        :param state_node: the state node that the event belongs to
        :param xpath: the xpath of the element to input text
        :param mock_strategy: the mock strategy to generate the input text
        :param text: the text to be input. If not provided, the mock strategy will be used to generate the text. Otherwise, the text will be used.
        """
        super(TextInputEvent, self).__init__(state_node)
        self.xpath = xpath
        self.mock_strategy = mock_strategy
        self.text = text

    def __str__(self):
        return f"TextInputEvent event_{self.event_id} on state_node_{self.state_node.id}: {self.xpath} (Mock Strategy: {self.mock_strategy}, Text: {self.text})"

    def perform(self, device_mng: DeviceManager):
        if self.text is None:
            text = self.mock_strategy.generate_text()
        else:
            text = self.text
        device_mng.text_input(self.xpath, text)

    def get_text(self):
        if self.text is None:
            text = self.mock_strategy.generate_text()
        else:
            text = self.text
        return text

    def to_dict(self) -> dict:
        return {
            "state_node_id": self.state_node.id,
            "event_id": self.event_id,
            "event_type": "text_input",
            "xpath": self.xpath,
            "mock_strategy": self.mock_strategy.to_dict(),
            "text": self.text
        }

class TextClearEvent(AbstractEvent):
    def __init__(self, state_node, xpath):
        """
        Create a text clear event
        :param state_node: the state node that the event belongs to
        :param xpath: the xpath of the element to be cleared
        """
        super(TextClearEvent, self).__init__(state_node)
        self.xpath = xpath

    def __str__(self):
        return f"TextClearEvent event_{self.event_id} on {self.state_node.id}"

    def perform(self, device_mng: DeviceManager):
        device_mng.text_clear(self.xpath)

    def to_dict(self) -> dict:
        return {
            "state_node_id": self.state_node.id,
            "event_id": self.event_id,
            "event_type": "text_clear",
            "xpath": self.xpath
        }

class BackEvent(AbstractEvent):

    def __init__(self, state_node):
        """
        Create a back event
        :param state_node: the state node that the event belongs to
        """
        super(BackEvent, self).__init__(state_node)

    def __str__(self):
        return f"BackEvent event_{self.event_id} on {self.state_node.id}"

    def perform(self, device_mng: DeviceManager):
        device_mng.back()

    def to_dict(self) -> dict:
        return {
            "state_node_id": self.state_node.id,
            "event_id": self.event_id,
            "event_type": "back"
        }

class InternalEvent(AbstractEvent):

    def __init__(self, state_node):
        """
        Create an internal event
        :param state_node: the state node that the event belongs to
        """
        super(InternalEvent, self).__init__(state_node)

    def __str__(self):
        return f"InternalEvent event_{self.event_id} on {self.state_node.id}"

    def perform(self, device_mng: DeviceManager):
        print(f"Event perform Error: Trying to perform an internal event {self.event_id}")
        raise NotImplementedError

    def to_dict(self) -> dict:
        return {
            "state_node_id": self.state_node.id,
            "event_id": self.event_id,
            "event_type": "internal"
        }


if __name__ == "__main__":
    from transition_graph.nodes.state_node import StateNode
    from transition_graph.utils.mock_strategy import MockStrategy

    # Usage example
    device_manager = DeviceManager(yaml_file_path="/Users/xingjunyang/Documents/GitHub/PathMuTeG/config.yaml")
    device_manager.start_package()
    state_node = StateNode("state_node_1", "<xml>...</xml>", "screenshot_path")
    click_event = TextInputEvent(state_node, '//android.widget.AutoCompleteTextView[@resource-id="com.github.characterdog.bmicalculator:id/txt_height"]', MockStrategy("symbol"))
    click_event.perform(device_manager)