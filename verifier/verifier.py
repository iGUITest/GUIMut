from time import sleep
import yaml


class Verifier:

    def __init__(self, yaml_file_path):
        from transition_graph import GraphManager

        self.yaml_file_path = yaml_file_path
        self.graph_mgr = GraphManager(yaml_file_path)
        self.graph_mgr.load_graph_from_file()
        self.script_path_state = None
        self.device_mgr = None
        self.state_mgr = None

        yaml_file = open(yaml_file_path, "r")
        config = yaml.safe_load(yaml_file)
        yaml_file.close()

        self.script_output_path = config["outputDir"] if "outputDir" in config else None
        self.app_name = config["appium"]["appPackage"]
        self.activity_name = config["appium"]["appActivity"]

    def verify(self, script_path, mutated_path):
        if self.script_path_state is None:
            [self.script_path_state, step] = self.__execute_path_and_capture_final_state(script_path, coverage_file_location="original")
        [mutated_path_state, step] = self.__execute_path_and_capture_final_state(mutated_path, coverage_file_location="mutated")
        if self.script_path_state is None or mutated_path_state is None:
            # print(f"Verification: The script path or the mutated path is invalid.")
            return [False, step]
        if self.graph_mgr.same_state_strategy.is_same_state(self.script_path_state, mutated_path_state):
            # print(f"Verification: The script path and the mutated path are equivalent.")
            return [True, step]
        else:
            # print(f"Verification: The script path and the mutated path are NOT equivalent.")
            return [False, step]

    def __execute_path_and_capture_final_state(self, path, coverage_file_location=None):
        """
        Execute the path and capture the final state.
        :param path: The path to execute.
        :return: [state, step] The final state after executing the path and the step executed.
        """
        from path_mapping.path_node import PathNode
        from transition_graph import StateManager
        from device_infrastructure import DeviceManager

        if self.device_mgr is not None:
            self.device_mgr.quit()
        self.device_mgr = DeviceManager(self.yaml_file_path)
        self.state_mgr = StateManager(self.device_mgr)

        path_array = path.to_array()

        for path_node in path_array:
            if isinstance(path_node, PathNode):
                current_state = self.state_mgr.capture_new_state()
                if not self.graph_mgr.same_state_strategy.is_same_state(path_node.state, current_state):
                    # print(f"Verification: The path node state and the current state are NOT equivalent.")
                    return [None, path_array.index(path_node)]
                if path_node.event is None:
                    if path_node != path_array[-1]:
                        # print(f"Verification: The path node event is None but not the last node.")
                        return [None, path_array.index(path_node)]
                    else:
                        continue
                path_node.event.perform(self.device_mgr)

        sleep(6) # wait for logs to be written
        self.device_mgr.save_coverage_file(coverage_file_location)

        final_state = self.state_mgr.capture_new_state()
        return [final_state, len(path_array)]

    def verify_batch(self, script_path, mutated_paths):
        """
        Verify a batch of mutated paths against the original script path.
        :param script_path: The original script path.
        :param mutated_paths: A list of mutated paths to verify.
        :return: A list of verification results for each mutated path.
        """
        results = []
        for mutated_path in mutated_paths:
            result = self.verify(script_path, mutated_path)
            results.append(result)

        return results

    def verify_batch_and_output_to_file(self, script_path, mutated_paths):
        """
        Verify a batch of mutated paths against the original script path and save the results to a file.
        :param script_path: The original script path.
        :param mutated_paths: A list of mutated paths to verify.
        """

        # init the output directory
        import os
        if self.script_output_path is not None:
            if not os.path.exists(self.script_output_path):
                os.makedirs(self.script_output_path)
        else:
            raise ValueError("Output directory is not specified in the YAML file.")


        results = []
        counter = 1
        for mutated_path in mutated_paths:
            result = self.verify(script_path, mutated_path)

            if result[0]:
                file_name = f"mutated_test_script_{counter}.py"
                with open(os.path.join(self.script_output_path, file_name), "w") as f:
                    from path_mapping import PathMapper
                    f.write(PathMapper.generate_script(mutated_path, self.app_name, self.activity_name))
                    f.close()
                counter += 1

            results.append(result)

        return results