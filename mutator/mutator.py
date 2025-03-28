import yaml
from time import sleep
from mutator.find_checkpoint import HeuristicFindCheckpointStrategy, ManualFindCheckpointStrategy


class Mutator:

    from path_mapping import Path

    def __init__(self, yaml_file_path, transition_graph_node):
        self.transition_graph_node = transition_graph_node

        yaml_file = open(yaml_file_path, "r")
        config = yaml.safe_load(yaml_file)
        yaml_file.close()

        self.max_path_length = config["mutation"]["maxPathLength"]
        self.max_mutations = config["mutation"]["maxMutations"]
        self.enabled_mrs = []

        for mr in config["MRs"]:
            find_checkpoint_mode = config["MRs"][mr]["find_checkpoint"]
            if find_checkpoint_mode not in ['auto', 'manual']:
                print("Invalid find checkpoint mode, skipping...")
                continue
            print(f"Loading MR: {mr} [find_checkpoint_mode: {find_checkpoint_mode}]")
            find_checkpoint_strategy = HeuristicFindCheckpointStrategy() if find_checkpoint_mode == "auto" else ManualFindCheckpointStrategy()
            if mr == "MRReplace" and config["MRs"][mr]["enabled"]:
                from mutator import MRReplace
                self.enabled_mrs.append(MRReplace(find_checkpoint_strategy, self.max_mutations, self.max_path_length))
            elif mr == "MRCycle" and config["MRs"][mr]["enabled"]:
                from mutator import MRCycle
                self.enabled_mrs.append(MRCycle(find_checkpoint_strategy, self.max_mutations, self.max_path_length))

    def mutate(self, path: Path) -> list[Path]:
        """
        Mutate a given path using the enabled metamorphic relations.

        :param path: The path to be mutated.
        :return: A list of mutated paths.
        """

        # Apply each enabled metamorphic relation to the path
        mutated_paths = []
        for mr in self.enabled_mrs:
            mutated_paths.extend(mr.mutate(path, self.transition_graph_node))

        # Filter the mutated paths to ensure they are valid and do not exceed the maximum path length
        filtered_paths = self.__filter_mutations(mutated_paths)

        return filtered_paths


    def __filter_mutations(self, mutations: list[Path]) -> list[Path]:
        """
        Customized rules to filter mutations. Default no filters.

        :param mutations: The list of mutated paths.
        :return: A filtered list of valid mutated paths.
        """
        return mutations

if __name__ == "__main__":
    yaml_file_path = "/Users/xingjunyang/Documents/GitHub/PathMuTeG/config.yaml"
    mutator = Mutator(yaml_file_path, None)
    mrs = mutator.enabled_mrs
    sleep(1)