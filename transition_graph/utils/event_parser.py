import xml.etree.ElementTree as ET
from time import sleep

from device_infrastructure import DeviceManager
from transition_graph.nodes.state_node import StateNode


def _get_xpath(element):
    """
    Generate an optimal XPath for an element.

    This function tries to find a unique XPath for the element, prioritizing:
    1. Unique attributes like resource-id
    2. Pairs of attributes that might be unique together
    3. 'Maybe' unique attributes
    4. Just the tag if it's unique
    5. A hierarchical path as a last resort

    Args:
        element: An ElementTree element

    Returns:
        str: An XPath string that uniquely identifies the element
    """

    # Attributes on nodes that are likely to be unique to the node so we should consider first when
    # suggesting xpath locators. These are considered IN ORDER.
    UNIQUE_XPATH_ATTRIBUTES = ['name', 'content-desc', 'id', 'resource-id', 'accessibility-id']

    # Attributes that we should recommend as a fallback but ideally only in conjunction with other
    # attributes
    MAYBE_UNIQUE_XPATH_ATTRIBUTES = ['label', 'text', 'value']

    def _get_root(element):
        """Find the root Element of the tree containing the element"""
        root = element
        while root.attrib.get('parent') is not None:
            root = root.attrib.get('parent')
        return root

    def _get_optimal_xpath(doc, element):
        """
        Get an optimal XPath for an element.

        Based on the getOptimalXPath function in the JavaScript file.

        Args:
            doc: Root document/element to test uniqueness against
            element: Element to generate XPath for

        Returns:
            str: Optimal XPath for the element
        """
        if element is None or not hasattr(element, 'tag'):
            return ''

        xpath = _try_unique_attribute_xpath(doc, element, UNIQUE_XPATH_ATTRIBUTES)
        if xpath:
            return xpath

        attr_pairs = _generate_attribute_pairs(UNIQUE_XPATH_ATTRIBUTES + MAYBE_UNIQUE_XPATH_ATTRIBUTES)
        xpath = _try_attribute_pairs_xpath(doc, element, attr_pairs)
        if xpath:
            return xpath

        xpath = _try_unique_attribute_xpath(doc, element, MAYBE_UNIQUE_XPATH_ATTRIBUTES)
        if xpath:
            return xpath

        xpath = _try_unique_tag_xpath(doc, element)
        if xpath:
            return xpath

        # Fall back to hierarchical XPath as a last resort
        return _get_hierarchical_xpath(doc, element)

    def _generate_attribute_pairs(attrs):
        """Generate all possible pairs of attributes from a list"""
        pairs = []
        for i in range(len(attrs)):
            for j in range(i + 1, len(attrs)):
                pairs.append((attrs[i], attrs[j]))
        return pairs

    def _try_unique_attribute_xpath(doc, element, attrs):
        """Try to find a unique XPath using a single attribute"""
        tag = element.tag

        for attr in attrs:
            if attr in element.attrib and element.attrib[attr]:
                # Create an XPath with this attribute
                attr_value = element.attrib[attr].replace('"', '\\"')
                xpath = f'//{tag}[@{attr}="{attr_value}"]'

                # Check if this XPath is unique
                is_unique, index = _determine_xpath_uniqueness(doc, xpath, element)
                if is_unique:
                    return xpath
                elif index is not None:
                    # If not unique but we have an index, create a semi-unique XPath
                    return f'({xpath})[{index + 1}]'

        return None

    def _try_attribute_pairs_xpath(doc, element, attr_pairs):
        """Try to find a unique XPath using pairs of attributes"""
        tag = element.tag

        for attr1, attr2 in attr_pairs:
            if attr1 in element.attrib and attr2 in element.attrib and element.attrib[attr1] and element.attrib[attr2]:
                # Create an XPath with this attribute pair
                attr1_value = element.attrib[attr1].replace('"', '\\"')
                attr2_value = element.attrib[attr2].replace('"', '\\"')
                xpath = f'//{tag}[@{attr1}="{attr1_value}" and @{attr2}="{attr2_value}"]'

                # Check if this XPath is unique
                is_unique, _ = _determine_xpath_uniqueness(doc, xpath, element)
                if is_unique:
                    return xpath

        return None

    def _try_unique_tag_xpath(doc, element):
        """Check if the tag name is unique in the document"""
        xpath = f'//{element.tag}'
        is_unique, _ = _determine_xpath_uniqueness(doc, xpath, element)

        if is_unique:
            # If this is the root element, use '/' instead of '//'
            parent = element.getparent() if hasattr(element, 'getparent') else None
            parent = element.attrib.get('parent') if parent is None and 'parent' in element.attrib else parent

            if parent is None:
                return f'/{element.tag}'
            return xpath

        return None

    def _get_hierarchical_xpath(doc, element):
        """Generate a hierarchical XPath as a last resort"""
        # First get the relative xpath of this node using tagName
        xpath = f'/{element.tag}'

        # Check if we need to add an index (for siblings with same tag)
        parent = element.getparent() if hasattr(element, 'getparent') else None
        parent = element.attrib.get('parent') if parent is None and 'parent' in element.attrib else parent

        if parent is not None:
            siblings = [child for child in parent if child.tag == element.tag]
            if len(siblings) > 1:
                index = siblings.index(element) if element in siblings else -1
                if index >= 0:
                    xpath += f'[{index + 1}]'

        # Make a recursive call to this node's parent and prepend it
        parent_xpath = _get_optimal_xpath(doc, parent)
        return parent_xpath + xpath

    def _determine_xpath_uniqueness(doc, xpath, target_element):
        """
        Determine if an XPath is unique in the document.

        Args:
            doc: Root document to search in
            xpath: XPath to check
            target_element: The target element we're trying to uniquely identify

        Returns:
            tuple: (is_unique, index_if_not_unique)
                - is_unique: True if the XPath uniquely identifies the element
                - index_if_not_unique: If not unique, the index of the target_element in the results
        """
        try:
            matches = doc.findall('.' + xpath)

            if len(matches) == 0:
                # No matches, so not unique (and broken)
                return False, None
            elif len(matches) == 1:
                # One match, it's unique!
                return True, None
            else:
                # Multiple matches, find our target's index
                for i, match in enumerate(matches):
                    if match == target_element:
                        return False, i

                # Didn't find our element in the matches (shouldn't happen)
                return False, None
        except Exception as e:
            print(f"Error evaluating XPath '{xpath}': {e}")
            return False, None


    root = _get_root(element)
    # remove the hierarchy prefix from the xpath
    optimal_xpath = _get_optimal_xpath(root, element).replace("hierarchy/", "", 1)
    return optimal_xpath

def _get_all_events_in_element(state_node, element_tree, tree_root):
    from transition_graph.events.event import ClickEvent, TextInputEvent, TextClearEvent
    from transition_graph.utils.mock_strategy import MockStrategy

    events = []
    for element in element_tree:
        element.attrib['parent'] = element_tree
        # get the xpath of the element
        if element.attrib.get('focusable') == 'true' and (element.attrib['class'] == 'android.widget.EditText' or element.attrib['class'] == 'android.widget.AutoCompleteTextView' or element.attrib['class'] == 'android.widget.TextView'):
            xpath = _get_xpath(element)
            if element.attrib['text'] != '':
                events.append(TextClearEvent(state_node, xpath))
                if not MockStrategy.is_in_hash_map(element.attrib['text']):
                    events.append(TextInputEvent(state_node, xpath, MockStrategy("number")))
            else:
                events.append(TextInputEvent(state_node, xpath, MockStrategy("number")))
                # events.append(TextInputEvent(state_node, xpath, MockStrategy("letter")))
                # events.append(TextInputEvent(state_node, xpath, MockStrategy("symbol")))
        if element.attrib.get('clickable') == 'true':
            xpath = _get_xpath(element)
            events.append(ClickEvent(state_node, xpath))
        events.extend(_get_all_events_in_element(state_node, element, tree_root))

    return events

def check_permission_controller(events):
    from transition_graph import ClickEvent
    for event in events:
        if isinstance(event, ClickEvent) and event.xpath == '//android.widget.Button[@resource-id="com.android.permissioncontroller:id/permission_allow_button"]':
            return [event]

    return events

def get_all_events_in_component_tree(state_node: StateNode, component_tree):
    """
        Get all events that can be triggered in the given component tree.

        :param state_node: The state node that the component tree belongs to
        :param component_tree: An XML-like string representing the component tree
        :return: A list of events that can be triggered in the component tree
        """
    from transition_graph.events.event import BackEvent

    root = ET.fromstring(component_tree)
    events = _get_all_events_in_element(state_node, root, root)
    events.append(BackEvent(state_node))

    events = check_permission_controller(events)
    # Add more event filters here if needed

    return events


if __name__ == "__main__":
    # test the function
    dm = DeviceManager(yaml_file_path="/Users/xingjunyang/Documents/GitHub/PathMuTeG/config.yaml")
    sleep(5)
    state_node = StateNode("state_node", dm.get_component_tree(), dm.take_screenshot())
    events = get_all_events_in_component_tree(state_node, state_node.component_tree)
    print("Events:")
    for event in events:
        print(event)