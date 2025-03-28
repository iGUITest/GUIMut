from device_infrastructure import DeviceInfraError


def jaccard_Similarity(path_array_a: list, path_array_b: list) -> float:
    # To calculate the Jaccard similarity of the two input path arrays.
    set_a = set(list(map(lambda path_node: path_node.state, path_array_a)))
    set_b = set(list(map(lambda path_node: path_node.state, path_array_b)))

    intersection = len(set_a.intersection(set_b))
    union = len(set_a.union(set_b))

    if union == 0:
        return 1.0
    else:
        return 1.0 * intersection / union

def calc_jaccard_similarity(original_path, validated_mutations):
    adr_o = 0.0
    adr_m = 0.0

    if len(validated_mutations) != 0:
        # Calculating ADR-O
        original_path_array = original_path.to_array()
        for i in range(len(validated_mutations)):
            mutated_path_array = validated_mutations[i].to_array()
            adr_o += jaccard_Similarity(original_path_array, mutated_path_array)
        adr_o /= len(validated_mutations)

        # Calculating ADR-G
        for i in range(len(validated_mutations)):
            for j in range(i):
                adr_m += jaccard_Similarity(validated_mutations[i].to_array(), validated_mutations[j].to_array())
        adr_m /= 1.0 * (len(validated_mutations) * (len(validated_mutations) - 1) / 2)
    else:
        adr_o = adr_m = 1.0

    return [adr_o, adr_m]


def levenshtein_distance(path_array_a: list, path_array_b: list) -> int:
    list_a = list(map(lambda path_node: path_node.state, path_array_a))
    list_b = list(map(lambda path_node: path_node.state, path_array_b))

    # calculate the levenshtein distance of list_a and list_b
    m, n = len(list_a), len(list_b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    # Initialize base cases
    for j in range(n + 1):
        dp[0][j] = j
    for i in range(m + 1):
        dp[i][0] = i

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if list_a[i - 1] == list_b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = min(
                    dp[i - 1][j - 1] + 1,  # Replace
                    dp[i - 1][j] + 1,  # Delete
                    dp[i][j - 1] + 1  # Insert
                )

    return dp[m][n]

def calc_levenshtein_distance(original_path, validated_mutations):
    adr_o = 0.0
    adr_m = 0.0

    if len(validated_mutations) != 0:
        # Calculating ADR-O
        original_path_array = original_path.to_array()
        for i in range(len(validated_mutations)):
            mutated_path_array = validated_mutations[i].to_array()
            adr_o += levenshtein_distance(original_path_array, mutated_path_array)
        adr_o /= len(validated_mutations)

        # Calculating ADR-G
        for i in range(len(validated_mutations)):
            for j in range(i):
                adr_m += levenshtein_distance(validated_mutations[i].to_array(), validated_mutations[j].to_array())
        adr_m /= 1.0 * (len(validated_mutations) * (len(validated_mutations) - 1) / 2)
    else:
        adr_o = adr_m = 1.0

    return [adr_o, adr_m]


def gui_explore(yaml_file_path, env_manager, logger, explore_id):
    import yaml
    import time
    import sys
    from pathlib import Path
    from gui_exploration.gui_explorer import GUIExplorer

    yaml_file = open(yaml_file_path, "r")
    config = yaml.safe_load(yaml_file)
    yaml_file.close()
    start_time = time.time()
    epoch_elapsed = 0
    err_count = 0
    explorer = GUIExplorer(yaml_file_path, epoch=epoch_elapsed, reset=True)

    if "logDir" in config:
        log_file_path = Path(config["logDir"]) / "gui_exploration.log"
        app_name = config["appium"]["appPackage"]
    else:
        print("Error: logDir not found in the configuration file.")
        return False

    while True:
        with open(log_file_path, "a") as log_file:
            sys.stdout = log_file
            sys.stderr = log_file
            env_manager.uninstall_apk(app_name)
            env_manager.install_apk(config["scriptDir"])
            try:
                while explorer.explore(app_name, logger) != "end":
                    pass
                
                env_manager.uninstall_apk(app_name)

                # Print the exploration results
                end_time = time.time()
                print(f"[GUI Explore {explore_id}] Time: {end_time - start_time} seconds")
                print(f"[GUI Explore {explore_id}] Epoch: {explorer.epoch}")
                print(f"[GUI Explore {explore_id}] One step time: {(end_time - start_time)/explorer.epoch} s/epoch")
                print(f"[GUI Explore {explore_id}] Graph nodes: {explorer.graph_mgr.calculate_states_count()}")
                print(f"[GUI Explore {explore_id}] Graph events: {explorer.graph_mgr.calculate_events_count()}")
                print(f"[GUI Explore {explore_id}] Graph transitions: {explorer.graph_mgr.calculate_transitions_count()}")

                # Log the exploration results
                logger.log(app_name, "script0", key="exp_t", value=end_time - start_time, phase="modeling")
                logger.log(app_name, "script0", key="exp_ep", value=explorer.epoch, phase="modeling")
                logger.log(app_name, "script0", key="states", value=explorer.graph_mgr.calculate_states_count(), phase="modeling")
                logger.log(app_name, "script0", key="events", value=explorer.graph_mgr.calculate_events_count(), phase="modeling")
                logger.log(app_name, "script0", key="trans", value=explorer.graph_mgr.calculate_transitions_count(), phase="modeling")

                try:
                    explorer.device_mgr.merge_coverage_files()
                    logger.calculate_coverage_stats(app_name, "script0", phase="modeling")
                except Exception as e:
                    print(f"Error calculating coverage: {e}")

                # Set the output back to the console
                sys.stdout = sys.__stdout__
                sys.stderr = sys.__stderr__
                print(f"GUI exploration of {app_name} completed. Log file saved at:", log_file_path)
                return True

            except DeviceInfraError as e:
                epoch_elapsed += explorer.epoch
                print(f"Device infrastructure error occurred: {e.message}. Retrying exploration...")
                env_manager.restart()
                explorer = GUIExplorer(yaml_file_path, epoch=epoch_elapsed, reset=False)
                err_count += 1
                if err_count > 5:
                    print("Error: Too many device infrastructure errors. Please check the configuration and try again.")
                    return False
            except Exception as e:
                end_time = time.time()
                print(f"[GUI Explore {explore_id}] GUI exploration time: {end_time - start_time} seconds")

                logger.log(app_name, "script0", key="exp_t", value=end_time - start_time, phase="modeling")

                sys.stdout = sys.__stdout__
                print(f"Error: {e} GUI exploration failed. Please check the configuration and try again.")
                return False

def path_mutate(yaml_file_path, env_manager, logger, mutate_id):
    import yaml
    import sys
    import time
    from path_mapping import PathMapper
    from mutator import Mutator
    from verifier import Verifier
    from pathlib import Path

    yaml_file = open(yaml_file_path, "r")
    config = yaml.safe_load(yaml_file)
    yaml_file.close()
    start_time = time.time()

    if "logDir" in config:
        log_file_path = Path(config["logDir"]) / "path_mutation.log"
        app_name = config["appium"]["appPackage"]
        script_name = config["scriptDir"].split("/")[-1]
    else:
        print("Error: logDir not found in the configuration file.")
        return False

    with open(log_file_path, "a") as log_file:
        sys.stdout = log_file
        sys.stderr = log_file
        env_manager.uninstall_apk(app_name)
        env_manager.install_apk(str(Path(config["scriptDir"]).parent.absolute()))
        try:
            path_mapper = PathMapper(yaml_file_path)
            path = path_mapper.map_path()
            path_mapper.device_mgr.quit()

            if len(path.to_array()) == 0:
                print(f"Path Mapping Failed!")

            gm = path_mapper.graph_mgr
            mt = Mutator(yaml_file_path, gm.currentGraph)
            mutations = mt.mutate(path)
            print(f"Generated {len(mutations)} Mutation(s).")
            logger.log(app_name, script_name, key="mut_cnt", value=len(mutations), phase="mutation")

            verifier = Verifier(yaml_file_path)
            result = verifier.verify_batch_and_output_to_file(path, mutations)

            validated_mutations = []
            for i, res in enumerate(result):
                print(f"Mutation {i}: {'Equivalent' if res[0] else 'Not Equivalent'} [Mutated Path Length: {len(mutations[i].to_array())}, Success Step: {res[1]}]")
                if res[0]:
                    validated_mutations.append(mutations[i])

            logger.log(app_name, script_name, key="gen_cnt", value=len(validated_mutations), phase="mutation")

            path_length = []
            for i in range(len(validated_mutations)):
                path_length.append(len(validated_mutations[i].to_array()))
            print(path_length)

            logger.log(app_name, script_name, key="steps", value=str(path_length), phase="mutation")
            
            [js_o, js_m] = calc_jaccard_similarity(path, mutations)
            [v_js_o, v_js_m] = calc_jaccard_similarity(path, validated_mutations)
            [ld_o, ld_m] = calc_levenshtein_distance(path, mutations)
            [v_ld_o, v_ld_m] = calc_levenshtein_distance(path, validated_mutations)

            logger.log(app_name, script_name, key="om_dst", value=ld_o, phase="mutation")
            logger.log(app_name, script_name, key="mm_dst", value=ld_m, phase="mutation")

            env_manager.uninstall_apk(app_name)

            end_time = time.time()
            print(f"[Path Mutate {mutate_id}] Path mutation time: {end_time - start_time} seconds")
            print(f"[Path Mutate {mutate_id}] Validated mutations Jaccard Similarity value: {v_js_o}(O-M), {v_js_m}(M-M)")
            print(f"[Path Mutate {mutate_id}] All mutations Jaccard Similarity value: {js_o}(O-M), {js_m}(M-M)")
            print(f"[Path Mutate {mutate_id}] Validated mutations Levenshtein Distance value: {v_ld_o}(O-M), {v_ld_m}(M-M)")
            print(f"[Path Mutate {mutate_id}] All mutations Levenshtein Distance value: {ld_o}(O-M), {ld_m}(M-M)")

            logger.log(app_name, script_name, key="mut_t", value=end_time - start_time, phase="mutation")

            try:
                verifier.device_mgr.merge_coverage_files(where="original")
                verifier.device_mgr.merge_coverage_files(where="mutated")
                logger.calculate_coverage_stats(app_name, script_name, phase="mutation")
            except Exception as e:
                print(f"Error calculating coverage: {e}")

            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
            print(f"Path mutation of {app_name} completed. Log file saved at:", log_file_path)
            return True

        except Exception as e:
            end_time = time.time()
            print(f"[Path Mutate {mutate_id}] Path mutation time: {end_time - start_time} seconds")

            logger.log(app_name, script_name, key="mut_t", value=end_time - start_time, phase="mutation")

            sys.stdout = sys.__stdout__
            print(f"Error: Path mutation failed. {e}")
            return False

def generate_yaml_file_for_this_script(main_yaml_file_path):
    import yaml
    from pathlib import Path

    with open(main_yaml_file_path, 'r') as file:
        config = yaml.safe_load(file)
        file.close()

    # Input Folder Structure
    # |-- input_folder
    #     |-- app_name1 (format: activity_name@package_name)
    #         |-- test_case1.py
    #         |-- test_case2.py
    #     |-- app_name2
    #         |-- test_case1.py

    # Output Folder Structure
    # |-- output_folder
    #     |-- app_name1
    #         |-- config.yaml
    #         |-- mutated_test_cases
    #             |-- test_case1
    #                 |-- config.yaml
    #                 |-- mutated_test_case1.py
    #                 |-- mutated_test_case2.py
    #             |-- test_case2
    #         |-- transition_graph
    #         |-- screenshots
    #         |-- logs
    #     |-- app_name2

    (Path(config["outputDir"])).mkdir(exist_ok=True)

    if config["statistics"]["enabled"]:
        (Path(config["statistics"]["outputDir"])).mkdir(exist_ok=True)

    input_folder_path = Path(config['scriptDir'])
    for dir_path in input_folder_path.iterdir():
        if dir_path.is_dir():
            app_name = dir_path.name.split('@')[1]  # Extract app name from the directory name
            activity_name = dir_path.name.split('@')[0]  # Extract activity name from the directory name

            output_folder_path = Path(config['outputDir']) / app_name
            output_folder_path.mkdir(parents=True, exist_ok=True)

            # Copy config.yaml to the output folder
            with open(main_yaml_file_path, 'r') as file:
                config_data = yaml.safe_load(file)
                file.close()

            # Create the output folder structure
            (output_folder_path / 'mutated_test_cases').mkdir(exist_ok=True)
            (output_folder_path / 'transition_graph').mkdir(exist_ok=True)
            (output_folder_path / 'screenshots').mkdir(exist_ok=True)
            (output_folder_path / 'logs').mkdir(exist_ok=True)
            if config["coverageFile"]:
                (output_folder_path / 'coverage_data').mkdir(exist_ok=True)

            # modify the config data
            config_data["appium"]["appPackage"] = app_name
            config_data["appium"]["appActivity"] = activity_name
            config_data["screenshotDir"] = str((output_folder_path / 'screenshots').absolute())
            config_data["graphDir"] = str((output_folder_path / 'transition_graph').absolute())
            config_data["scriptDir"] = str(dir_path.absolute())
            config_data["logDir"] = str((output_folder_path / 'logs').absolute())
            if config["coverageFile"]:
                config_data["coverageFileDir"] = str((output_folder_path / 'coverage_data').absolute())

            with open(output_folder_path / 'config.yaml', 'w') as file:
                yaml.dump(config_data, file)
                file.close()

            # iterate through the test cases in the input folder
            for test_case_file in dir_path.iterdir():
                if test_case_file.is_file() and test_case_file.suffix == '.py':
                    test_case_name = test_case_file.stem
                    mutated_test_case_folder = output_folder_path / 'mutated_test_cases' / test_case_name
                    mutated_test_case_folder.mkdir(parents=True, exist_ok=True)

                    config_data["scriptDir"] = str(test_case_file.absolute())
                    config_data["outputDir"] = str(mutated_test_case_folder.absolute())

                    with open(mutated_test_case_folder / 'config.yaml', 'w') as file:
                        yaml.dump(config_data, file)
                        file.close()

def main():
    import argparse
    parser = argparse.ArgumentParser(
        prog='main.py',
        description='[GUIMut@IGUITest] A mobile test generation tool based on metamorphic relation-understood path mutation.',
        epilog='Visit our repo: https://github.com/iGUITest/GUIMut'
    )
    parser.add_argument('-f', '--config-file', dest='yaml_file_path', help='Specify Yaml config file path. See README.md or our default config file for more help.', default='./config.yaml')
    parser.add_argument('-e', '--explore-only', dest='gui_explore_only', help='Explore the GUI without path mutation.', action='store_true')
    parser.add_argument('-m', '--mutate-only', dest='path_mutate_only', help='Mutate without exploring the GUI in real-time, but read the data from previous exploration.', action='store_true')
    args = parser.parse_args()

    # Print Config
    config_info = f"""GUIMut@IGUITest
-------------------------
Config File: {args.yaml_file_path}
"""
    if args.gui_explore_only:
        config_info += "Mode: GUI Explore Only"
    if args.path_mutate_only:
        config_info += "Mode: Path Mutate Only"
    config_info += "\n-------------------------\n"
    print(config_info)

    main_yaml_file_path = args.yaml_file_path
    generate_yaml_file_for_this_script(main_yaml_file_path)

    import yaml
    from pathlib import Path
    from device_infrastructure import EnvManager
    from statistic import Logger

    env_manager = EnvManager(main_yaml_file_path)

    logger = Logger(main_yaml_file_path)

    with open(main_yaml_file_path, 'r') as file:
        config = yaml.safe_load(file)
        file.close()

    output_path = Path(config['outputDir'])

    # Check if the output path exists
    if output_path.exists():
        print(f"Output path {output_path} exists.")
    else:
        print(f"Output path {output_path} does not exist.")
        exit(1)

    if not args.path_mutate_only:
        # gui_explore
        explore_id = 0
        for dir_path in output_path.iterdir():
            if dir_path.is_dir():
                if dir_path.name == 'statistics':
                    continue
                yaml_file_path = dir_path / 'config.yaml'

                if yaml_file_path.exists():
                    print(f"[GUI Explore {explore_id}] YAML file {yaml_file_path} exists.")
                    gui_explore(yaml_file_path, env_manager, logger, explore_id)
                else:
                    print(f"[GUI Explore {explore_id}] YAML file {yaml_file_path} does not exist.")
                    exit(1)
                explore_id += 1
                env_manager.restart()
                logger.export("modeling")

    if not args.gui_explore_only:
        # path_mutate
        mutate_id = 0
        for dir_path in output_path.iterdir():
            if dir_path.is_dir():
                if dir_path.name == 'statistics':
                    continue
                for mutated_test_case_folder in (dir_path / 'mutated_test_cases').iterdir():
                    if mutated_test_case_folder.is_dir():
                        if not mutated_test_case_folder.name.startswith('script'):
                            continue

                        yaml_file_path = mutated_test_case_folder / 'config.yaml'
                        if yaml_file_path.exists():
                            print(f"[Path Mutate {mutate_id}] YAML file {yaml_file_path} exists.")
                            path_mutate(yaml_file_path, env_manager, logger, mutate_id)
                        else:
                            print(f"[Path Mutate {mutate_id}] YAML file {yaml_file_path} does not exist.")
                            exit(1)
                        mutate_id += 1

                logger.export("mutation")

if __name__ == "__main__":
    main()