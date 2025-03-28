import yaml
from time import sleep


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
            print(f"Loading MR: {mr}")
            if mr == "MRPlainPath" and config["MRs"][mr]["enabled"]:
                from mutator import MRPlainPath
                self.enabled_mrs.append(MRPlainPath(self.max_mutations, self.max_path_length))
            elif mr == "MREnvironment" and config["MRs"][mr]["enabled"]:
                from mutator import MREnvironment
                mr_env_config = config["MRs"][mr]
                self.enabled_mrs.append(MREnvironment(self.max_mutations, self.max_path_length, mr_env_config))
            elif mr == "MRReplace" and config["MRs"][mr]["enabled"]:
                from mutator import MRReplace
                self.enabled_mrs.append(MRReplace(self.max_mutations, self.max_path_length))
            elif mr == "MRCycle" and config["MRs"][mr]["enabled"]:
                from mutator import MRCycle
                self.enabled_mrs.append(MRCycle(self.max_mutations, self.max_path_length))

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
        Filter the mutations to ensure they are valid and do not exceed the maximum path length.
        A priority algorithm shall be used to select the most promising mutations.

        :param mutations: The list of mutated paths.
        :return: A filtered list of valid mutated paths.
        """

        # TODO: Implement the filtering logic to ensure valid mutations.
        return mutations

if __name__ == "__main__":
    yaml_file_path = "/Users/xingjunyang/Documents/GitHub/PathMuTeG/config.yaml"
    mutator = Mutator(yaml_file_path, None)
    mrs = mutator.enabled_mrs
    sleep(1)