from time import sleep

import yaml


class PathMapper:

    from path_mapping import Path
    from transition_graph.events.event import AbstractEvent

    def __init__(self, yaml_file_path):
        from transition_graph import GraphManager, StateManager
        from device_infrastructure import DeviceManager

        self.device_mgr = DeviceManager(yaml_file_path, reset=False)
        self.graph_mgr = GraphManager(yaml_file_path)
        self.state_mgr = StateManager(self.device_mgr)
        self.graph_mgr.load_graph_from_file()
        self.transition_graph_node = self.graph_mgr.currentGraph

        yaml_file = open(yaml_file_path, "r")
        config = yaml.safe_load(yaml_file)
        yaml_file.close()

        self.script_path = config["scriptDir"] if "scriptDir" in config else None
        self.script_content = None
        self.delay = config["delay"] if "delay" in config else 1

        if self.script_path is None:
            raise ValueError("scriptDir not found in the configuration file. Path mapping aborted.")

    def map_path(self) -> Path:
        """
        Map the path of the script to the corresponding path in the graph.
        :return: A Path object representing the mapped path.
        """

        from path_mapping.path_node import PathNode, InternalPathNode
        from transition_graph.nodes.state_node import StateNode, InternalStateNode
        from path_mapping.path import Path
        # read the script file
        with open(self.script_path, "r") as script_file:
            self.script_content = script_file.read()
            script_file.close()

        # extract the steps from the script
        steps = self.__extract_steps(self.script_content)

        # match the steps with the transition graph
        path = Path()
        current_state = self.transition_graph_node.start_state

        for step in steps:
            transitions = current_state.transitions
            # transition: {event -> target_state_node}
            events = transitions.keys()
            matched_event = self.__match_step_and_event(step, current_state.component_tree, events)
            if matched_event is None:
                print(f"Error: No matching event found for step: {step}. Path mapping aborted without a valid path.")
                return Path()

            path.add_path_node(PathNode(current_state, matched_event))

            # perform the action on the device
            matched_event.perform(self.device_mgr)

            # get the target state node
            target_state_node = transitions[matched_event]
            if isinstance(target_state_node, InternalStateNode):
                current_device_state = self.state_mgr.capture_new_state()
                corresponding_state = None
                # check whether the corresponding_state in the target_state_node's transitions
                for nominate_state_node in target_state_node.transitions.values():
                    if self.graph_mgr.same_state_strategy.is_same_state(nominate_state_node, current_device_state):
                        corresponding_state = nominate_state_node
                        break
                if corresponding_state is None:
                    print(f"Error: The corresponding state {corresponding_state} is not in the target state node's transitions.")
                    return Path()
                # find the event that leads to the corresponding state
                target_event = None
                for event, target_state in target_state_node.transitions.items():
                    if target_state == corresponding_state:
                        target_event = event
                        break
                if target_event is None:
                    print(f"Error: No event found that leads to the corresponding state {corresponding_state}.")
                    return Path()
                path.add_path_node(InternalPathNode(target_state_node, target_event))
                target_state_node = corresponding_state

            # delay
            sleep(self.delay)

            current_state = target_state_node


        return path


    @staticmethod
    def __extract_steps(script_content):
        steps = []
        lines = script_content.split('\n')

        current_element = None
        current_locator = None

        for line in lines:
            if "driver.back()" in line:
                steps.append({
                    "action": "back",
                    "locator": None
                })
                continue
            # element locator
            if "find_element" in line and "=" in line:
                locator_parts = line.split("find_element")
                if len(locator_parts) > 1:
                    locator_method = locator_parts[1].strip('(').strip(')').split(",")[0].strip().replace("by=", "")
                    locator_value = locator_parts[1].strip('(').strip(')').split(",")[1].strip().replace("value=", "").strip('\'').strip('\"')

                    var_name = line.split("=")[0].strip()

                    current_element = var_name
                    current_locator = {"method": locator_method, "value": locator_value}

            # element action
            elif current_element and current_element in line:
                if ".send_keys" in line:
                    input_value = line.replace("\'", "\"").split('send_keys("')[1].split('")')[0]
                    steps.append({
                        "action": "send_keys",
                        "locator": current_locator,
                        "value": input_value
                    })
                elif ".click" in line:
                    steps.append({
                        "action": "click",
                        "locator": current_locator
                    })

        return steps


    @staticmethod
    def __match_step_and_event(step, component_tree, events: list[AbstractEvent]) -> AbstractEvent:
        """
        Match the step with the events in the transition graph.
        :param step: The step to be matched.
        :param events: The list of events in the transition graph.
        :return: The matched event. If no event is found, return None.
        """
        from transition_graph.events.event import ClickEvent, TextInputEvent, BackEvent

        for event in events:
            if step["action"] == "click" and isinstance(event, ClickEvent):
                if step["locator"]["method"] == 'AppiumBy.XPATH' and PathMapper.__compare_xpath(component_tree, event.xpath, step["locator"]["value"]):
                    return event
            elif step["action"] == "send_keys" and isinstance(event, TextInputEvent):
                if step["locator"]["method"] == 'AppiumBy.XPATH' and PathMapper.__compare_xpath(component_tree, event.xpath, step["locator"]["value"]):
                    return event
            elif step["action"] == "back" and isinstance(event, BackEvent):
                return event

        # TODO: Add more event types to match with the step

        return None

    @staticmethod
    def __compare_xpath(component_tree, xpath1, xpath2):
        xpath1 = xpath1.replace("'", "\"")
        xpath2 = xpath2.replace("'", "\"")
        xpath1 = xpath1.replace('"', "\"")
        xpath2 = xpath2.replace('"', "\"")
        xpath1 = xpath1.strip()
        xpath2 = xpath2.strip()

        from lxml import etree

        try:
            xml_bytes = component_tree.encode('utf-8')  # Convert to bytes
            root = etree.fromstring(xml_bytes)

            elements1 = root.xpath(xpath1)
            elements2 = root.xpath(xpath2)

            if len(elements1) == 1 and len(elements2) == 1:
                # if the two elements are the same, return True
                if elements1[0] == elements2[0]:
                    return True
                # if one element is a child of the other, return True
                if elements1[0].getparent() == elements2[0] or elements2[0].getparent() == elements1[0]:
                    return True
                # if the boundary of one element is contained in the other, return True
                bounds1 = elements1[0].get('bounds')
                bounds2 = elements2[0].get('bounds')
                #  bounds: [x1,y1][x2,y2]
                if bounds1 and bounds2:
                    x1, y1, x2, y2 = map(int, bounds1.replace('][', ',').replace('[', '').replace(']', '').split(','))
                    x3, y3, x4, y4 = map(int, bounds2.replace('][', ',').replace('[', '').replace(']', '').split(','))
                    if (x1 <= x3 <= x2 and y1 <= y3 <= y2 and x1 <= x4 <= x2 and y1 <= y4 <= y2) or \
                            (x3 <= x1 <= x4 and y3 <= y1 <= y4 and x3 <= x2 <= x4 and y3 <= y2 <= y4):
                        return True

                return False
            elif len(elements1) == 0 and len(elements2) == 0:
                # 如果两者都找不到任何节点，则认为它们不相等（maybe not）
                return False
            else:
                return set(elements1) == set(elements2)

        except etree.XMLSyntaxError:
            return False
        except etree.XPathEvalError:
            return False


    @staticmethod
    def generate_script(path, app_name, activity_name) -> str:
        """
        Map the path to the corresponding script.
        :param path: The path to be mapped.
        :return: The mapped script.
        """

        from path_mapping.path_node import PathNode

        output_stream = ""

        output_stream += f"# This script is generated by PathMuTeG.\n"
        output_stream += f"""
# This sample code supports Appium Python client >=2.3.0
# pip install Appium-Python-Client
# Then you can paste this into a file and simply run with Python

from appium import webdriver
from appium.options.common.base import AppiumOptions
from appium.webdriver.common.appiumby import AppiumBy

# For W3C actions
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions import interaction
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput

options = AppiumOptions()
options.load_capabilities({{
	"platformName": "Android",
	"appium:automationName": "uiautomator2",
	"appium:deviceName": "android",
	"appium:appPackage": "{app_name}",
	"appium:appActivity": "{activity_name}",
	"appium:language": "en",
	"appium:locale": "US",
	"appium:serverUrl": "http://localhost:4723",
	"appium:ensureWebviewsHavePages": True,
	"appium:nativeWebScreenshot": True,
	"appium:newCommandTimeout": 3600,
	"appium:connectHardwareKeyboard": True
}})

driver = webdriver.Remote("http://127.0.0.1:4723", options=options)


"""

        from transition_graph.events.event import TextInputEvent, TextClearEvent, BackEvent, ClickEvent

        path_array = path.to_array()
        counter = 0
        for path_node in path_array:
            if isinstance(path_node, PathNode):
                event = path_node.event
                if isinstance(event, TextInputEvent):
                    output_stream += f"el{counter} = driver.find_element(by=AppiumBy.XPATH, value='{event.xpath}')\n"
                    output_stream += f"el{counter}.send_keys(\"{event.get_text()}\")\n"
                elif isinstance(event, ClickEvent):
                    output_stream += f"el{counter} = driver.find_element(by=AppiumBy.XPATH, value='{event.xpath}')\n"
                    output_stream += f"el{counter}.click()\n"
                elif isinstance(event, TextClearEvent):
                    output_stream += f"el{counter} = driver.find_element(by=AppiumBy.XPATH, value='{event.xpath}')\n"
                    output_stream += f"el{counter}.clear()\n"
                elif isinstance(event, BackEvent):
                    output_stream += f"driver.back()\n"

                output_stream += "\n"
                counter += 1

        output_stream += f"driver.quit()\n"
        output_stream += f"# End of the script.\n"

        return output_stream

if __name__ == "__main__":
    from mutator import Mutator

    yaml_file_path = "/Users/xingjunyang/Documents/School/大一下/软工一/python/GUIMut/path_mapping/config.yaml"
    path_mapper = PathMapper(yaml_file_path)
    path = path_mapper.map_path()
    path_mapper.device_mgr.quit()

    path_arr = path.to_array()
    print(path_arr)

    gm = path_mapper.graph_mgr
    mt = Mutator(yaml_file_path, gm.currentGraph)
    mutations = mt.mutate(path)
    print(f"Generated {len(mutations)} Mutation(s).")

    from verifier import Verifier
    verifier = Verifier(yaml_file_path)
    result = verifier.verify_batch_and_output_to_file(path, mutations)

    for i, res in enumerate(result):
        print(f"Mutation {i}: {'Equivalent' if res[0] else 'Not Equivalent'} [Mutated Path Length: {len(mutations[i].to_array())}, Success Step: {res[1]}]")

    length = []
    for i in range(len(mutations)):
        length.append(len(mutations[i].to_array()))
    print(length)