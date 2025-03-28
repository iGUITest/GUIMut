from pathlib import Path
from typing import Dict, Optional, Union, Any
from .coverage_utils import generate_coverage_report, calculate_coverage_ratio, calculate_coverage_lines

class Logger:
    """
    A class for logging the results of the experiment.
    Log Data while the experiment is running.
    Export the data to CSV when the experiment is done.
    
    Data is stored using a composite key of (app_name, script_id) to support
    multiple script_ids for the same app_name without overwriting.
    """
    app_log: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict] = None
    metadata_path: Optional[str] = None
    statistics_output_path: Optional[str] = None
    output_path: Optional[str] = None
    enabled = False

    def __init__(self, yaml_file_path):
        import yaml

        self.yaml_file_path = yaml_file_path
        yaml_file = open(yaml_file_path, "r")
        config = yaml.safe_load(yaml_file)
        yaml_file.close()

        self.enabled = config["statistics"]["enabled"]
        self.statistics_output_path = config["statistics"]["outputDir"]
        self.metadata_path = config["statistics"]["metadataPath"]
        self.output_path = config["outputDir"]

        self.load_metadata()
        self.load_logs()

        print("[INFO] Logger initialized.")

    def load_metadata(self):
        import yaml

        if not self.enabled:
            print("[INFO] Statistics logging is disabled. Skipping metadata loading.")
            return
        
        if self.metadata_path is None:
            print("[ERROR] Metadata path is not configured.")
            return
        
        metadata_yaml_file = open(file=self.metadata_path, mode="r")
        self.metadata = yaml.safe_load(metadata_yaml_file)
        metadata_yaml_file.close()

        # Create a mapping of app_name to category for quick lookup
        self.app_to_category = {}
        if self.metadata and "app" in self.metadata:
            for app_info in self.metadata["app"]:
                app_name = app_info.get("name")
                category = app_info.get("category")
                if app_name and category:
                    self.app_to_category[app_name] = category

        return
    
    def load_logs(self):
        """
        Load previous logs from CSV files if they exist.
        Reads from {statistics_output_path}/results_mutation.csv and 
        {statistics_output_path}/results_modeling.csv and loads them into self.app_log.
        """
        if not self.enabled:
            print("[INFO] Statistics logging is disabled. Skipping log loading.")
            return
        
        if self.statistics_output_path is None:
            print("[ERROR] Statistics output path not configured.")
            return
        
        import os
        import csv
        from pathlib import Path
        
        if self.app_log is None:
            self.app_log = {}
        
        modeling_csv_path = os.path.join(self.statistics_output_path, "results_modeling.csv")
        if os.path.exists(modeling_csv_path):
            self._load_logs_from_csv(modeling_csv_path, "modeling")
        
        mutation_csv_path = os.path.join(self.statistics_output_path, "results_mutation.csv")
        if os.path.exists(mutation_csv_path):
            self._load_logs_from_csv(mutation_csv_path, "mutation")
        
        print(f"[INFO] Loaded previous logs. Total entries: {len(self.app_log)}")
    
    def _load_logs_from_csv(self, csv_path, phase):
        """
        Helper method to load logs from a CSV file.
        
        Args:
            csv_path: Path to the CSV file
            phase: The phase (modeling or mutation)
        """
        import csv
        import os
        
        if not os.path.exists(csv_path):
            return
        
        if self.app_log is None:
            self.app_log = {}
        
        try:
            with open(csv_path, "r", newline="") as csvfile:
                reader = csv.reader(csvfile)
                headers = next(reader)
                
                # Find indices for required columns
                last_timestamp_idx = headers.index("last_timestamp") if "last_timestamp" in headers else None
                app_name_idx = headers.index("app_name") if "app_name" in headers else None
                script_id_idx = headers.index("script_id") if "script_id" in headers else None
                
                if app_name_idx is None or script_id_idx is None:
                    print(f"[ERROR] Required columns missing in {csv_path}")
                    return
                
                key_columns = [h for h in headers if h not in ["last_timestamp", "app_name", "script_id"]]
                
                for row in reader:
                    if len(row) < max(filter(None, [last_timestamp_idx, app_name_idx, script_id_idx])) + 1:
                        continue  # Skip incomplete rows
                    
                    app_name = row[app_name_idx]
                    script_id = row[script_id_idx]
                    
                    composite_key = f"{app_name}#{script_id}"
                    
                    if composite_key not in self.app_log:
                        self.app_log[composite_key] = {
                            "app_name": app_name,
                            "script_id": script_id
                        }
                    
                    if phase not in self.app_log[composite_key]:
                        self.app_log[composite_key][phase] = {
                            "last_timestamp": 0,
                            "data": {}
                        }
                    
                    if last_timestamp_idx is not None and last_timestamp_idx < len(row):
                        try:
                            timestamp = float(row[last_timestamp_idx])
                            self.app_log[composite_key][phase]["last_timestamp"] = timestamp
                        except (ValueError, IndexError):
                            pass  # Keep default timestamp
                    
                    # Load key-value pairs
                    for key in key_columns:
                        if key in headers:
                            key_idx = headers.index(key)
                            if key_idx < len(row) and row[key_idx] != "":
                                # Try to convert to appropriate type based on metadata
                                value = row[key_idx]
                                if self.metadata and phase in self.metadata["keys"] and key in self.metadata["keys"][phase]:
                                    expected_type = self.metadata["keys"][phase][key].get("type", "str")
                                    try:
                                        if expected_type == "int":
                                            value = int(value)
                                        elif expected_type == "float":
                                            value = float(value)
                                        # For "str" type, keep as string
                                    except (ValueError, TypeError):
                                        # Keep original value if conversion fails
                                        pass
                                
                                self.app_log[composite_key][phase]["data"][key] = value
        except Exception as e:
            print(f"[ERROR] Failed to load logs from {csv_path}: {e}")

    def log(self, app_name, script_id, key, value, phase):
        if not self.enabled:
            print("[INFO] Statistics logging is disabled. Nothing to log.")
            return
        
        if self.metadata is None:
            print("[ERROR] Metadata not loaded. Cannot validate logging data.")
            return
        
        # Validate app_name
        if hasattr(self, 'app_to_category') and app_name not in self.app_to_category:
            print(f"[ERROR] App '{app_name}' not found in metadata. Valid apps examples: {list(self.app_to_category.keys())[:5]}...")
            return
        
        # Initialize app_log if it doesn't exist
        if self.app_log is None:
            self.app_log = {}
        
        # Validate phase
        valid_phases = ["modeling", "mutation"]
        if phase not in valid_phases:
            print(f"[ERROR] Invalid phase '{phase}'. Valid phases are: {valid_phases}")
            return
        
        # Validate key exists in metadata for the given phase
        if phase not in self.metadata["keys"]:
            print(f"[ERROR] Phase '{phase}' not found in metadata.")
            return
        
        if key not in self.metadata["keys"][phase]:
            print(f"[ERROR] Key '{key}' not found in metadata for phase '{phase}'.")
            return
        
        # Get metadata for the key
        key_metadata = self.metadata["keys"][phase][key]
        expected_type = key_metadata["type"]

        if key_metadata["is_caculated"] == True:
            print(f"[ERROR] Key '{key}' cannot be written for phase '{phase}'. It will be calculated automatically.")
            return
        
        # Validate value type
        type_mapping = {
            "int": int,
            "float": float,
            "str": str
        }
        
        if expected_type not in type_mapping:
            print(f"[ERROR] Unknown type '{expected_type}' for key '{key}'.")
            return
        
        if not isinstance(value, type_mapping[expected_type]):
            print(f"[ERROR] Value '{value}' is not of expected type '{expected_type}' for key '{key}'.")
            return
        
        # Get current timestamp
        import time
        current_timestamp = time.time()
        
        # Create composite key for app_name and script_id
        composite_key = f"{app_name}#{script_id}"
        
        # Initialize composite key entry if it doesn't exist
        if composite_key not in self.app_log:
            self.app_log[composite_key] = {
                "app_name": app_name,
                "script_id": script_id
            }
        
        # Initialize phase entry if it doesn't exist
        if phase not in self.app_log[composite_key]:
            self.app_log[composite_key][phase] = {
                "last_timestamp": current_timestamp,
                "data": {}
            }
        
        # Update the log entry for this phase
        self.app_log[composite_key][phase]["last_timestamp"] = current_timestamp
        
        # Add the key-value pair
        self.app_log[composite_key][phase]["data"][key] = value
        
        print(f"[INFO] Logged {key}={value} for app {app_name}, script {script_id} in phase {phase}")
        
        return

    def _calculate_metrics(self, phase, data_dict, app_data):
        """
        Calculate computed metrics based on phase and available data.
        
        Args:
            phase: The phase for which to calculate metrics
            data_dict: The data dictionary for the current phase
            app_data: All data for the current app (across all phases)
            
        Returns:
            dict: Dictionary with calculated metric values
        """
        calculated_values = {}
        
        if phase == "modeling":
            # exp_st = exp_t / exp_ep
            exp_t = data_dict.get("exp_t")
            exp_ep = data_dict.get("exp_ep")
            if exp_t is not None and exp_ep is not None:
                if exp_ep == 0:
                    calculated_values["exp_st"] = "N/A"
                else:
                    calculated_values["exp_st"] = exp_t / exp_ep
            
            # cc = cl/(cl+ucl)
            cl = data_dict.get("cl")
            ucl = data_dict.get("ucl")
            if cl is not None and ucl is not None:
                if (cl + ucl) == 0:
                    calculated_values["cc"] = "N/A"
                else:
                    calculated_values["cc"] = cl / (cl + ucl)
        
        elif phase == "mutation":
            # vr = gen_cnt/mut_cnt
            gen_cnt = data_dict.get("gen_cnt")
            mut_cnt = data_dict.get("mut_cnt")
            if gen_cnt is not None and mut_cnt is not None:
                if mut_cnt == 0:
                    calculated_values["vr"] = "N/A"
                else:
                    calculated_values["vr"] = gen_cnt / mut_cnt
        
        return calculated_values
    
    def calculate_coverage_stats(self, app_name, script_id, phase):
        if self.metadata is None or self.output_path is None:
            print("[ERROR] Failed to load metadata.")
            return
        if not self.enabled:
            print("[INFO] Statistics logging is disabled. Skipping coverage stats calculation.")
            return
        
        # Find the app data in the metadata list
        app_data = None
        for app in self.metadata["app"]:
            if app["name"] == app_name:
                app_data = app
                break
        
        if app_data is None:
            print(f"[ERROR] App '{app_name}' not found in metadata.")
            return
        
        app_src_cwd = str((Path(self.metadata["src_dir"]) / Path(app_data["src"]["location"])).absolute())
        coverage_file_input_path = str((Path(self.metadata["src_dir"]) / Path(app_data["src"]["location"]) / Path(app_data["src"]["cov_input_location"])).absolute())
        report_file_output_location = str((Path(self.metadata["src_dir"]) / Path(app_data["src"]["location"]) / Path(app_data["src"]["report_output_location"])).absolute())
        jdk_version = app_data["src"]["jdk_ver"]
        gradle_task_name = app_data["src"]["gradle_task_name"] if "gradle_task_name" in app_data["src"] else "jacocoManualReport"
        gradle_args = app_data["src"]["gradle_args"] if "gradle_args" in app_data["src"] else []

        if phase == "modeling":
            coverage_file_path = str((Path(self.output_path) / app_name / "coverage_data" / "coverage.ec").absolute())
            try:
                report_file_output_location = generate_coverage_report(app_src_cwd, coverage_file_path, coverage_file_input_path, report_file_output_location, gradle_task_name, gradle_args, jdk_version)
                if report_file_output_location is None:
                    print("[ERROR] Failed to generate coverage report for modeling phase.")
                    return
            except Exception as e:
                print(f"[ERROR] Exception during coverage report generation for modeling phase: {e}")
                return
            [cov, tot] = calculate_coverage_lines(report_file_output_location)
            self.log(app_name, script_id, "ucl", tot-cov, phase)
            self.log(app_name, script_id, "cl", cov, phase)
        elif phase == "mutation":
            coverage_file_path_original = str((Path(self.output_path) / app_name / "coverage_data" / "original" / "coverage.ec").absolute())
            coverage_file_path_mutated = str((Path(self.output_path) / app_name / "coverage_data" / "mutated" / "coverage.ec").absolute())
            try:
                report_file_output_location_original = generate_coverage_report(app_src_cwd, coverage_file_path_original, coverage_file_input_path, report_file_output_location, gradle_task_name, gradle_args, jdk_version)
                report_file_output_location_mutated = generate_coverage_report(app_src_cwd, coverage_file_path_mutated, coverage_file_input_path, report_file_output_location, gradle_task_name, gradle_args, jdk_version)
                
                if report_file_output_location_original is None or report_file_output_location_mutated is None:
                    print("[ERROR] Failed to generate one or both coverage reports for mutation phase.")
                    return
            except Exception as e:
                print(f"[ERROR] Exception during coverage report generation for mutation phase: {e}")
                return
            [ccr, dcr] = calculate_coverage_ratio(report_file_output_location_original, report_file_output_location_mutated)
            self.log(app_name, script_id, "ccr", ccr, phase)
            self.log(app_name, script_id, "dcr", dcr, phase)
            

    def export(self, phase):
        if not self.enabled:
            print("[INFO] Statistics logging is disabled. Skipping export.")
            return
        
        if self.app_log is None or len(self.app_log) == 0:
            print("[INFO] No data to export.")
            return
        
        if self.metadata is None:
            print("[ERROR] Metadata not loaded. Cannot export data.")
            return
        
        if self.statistics_output_path is None:
            print("[ERROR] Statistics output path not configured.")
            return
        
        import csv
        import os
        
        os.makedirs(self.statistics_output_path, exist_ok=True)
        
        # Get all keys for the specified phase from metadata
        if phase not in self.metadata["keys"]:
            print(f"[ERROR] Phase '{phase}' not found in metadata.")
            return
        
        phase_keys = list(self.metadata["keys"][phase].keys())

        headers = ["last_timestamp", "app_name", "script_id"] + phase_keys
        
        export_data = []
        for composite_key, entry_data in self.app_log.items():
            if phase in entry_data:
                app_name = entry_data["app_name"]
                script_id = entry_data["script_id"]
                phase_data = entry_data[phase]
                export_data.append((app_name, script_id, phase_data, entry_data))
        
        # Sort by app_name first, then by script_id
        export_data.sort(key=lambda x: (x[0], x[1]))
        
        csv_file_path = os.path.join(self.statistics_output_path, f"results_{phase}.csv")
        
        with open(csv_file_path, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            
            writer.writerow(headers)
            
            for app_name, script_id, phase_data, entry_data in export_data:
                row = [
                    phase_data.get("last_timestamp", ""),
                    app_name,
                    script_id
                ]
                
                # Add values for each key in the phase, using default if not present
                data_dict = phase_data.get("data", {})
                
                calculated_metrics = self._calculate_metrics(phase, data_dict, entry_data)
                
                for key in phase_keys:
                    key_metadata = self.metadata["keys"][phase][key]
                    
                    if key_metadata.get("is_caculated", False):
                        # Use calculated value if available
                        if key in calculated_metrics:
                            row.append(calculated_metrics[key])
                        else:
                            # Use default value if calculation not available
                            default_value = key_metadata.get("default", "")
                            row.append(default_value)
                    else:
                        # Use logged value if available, otherwise use default
                        value = data_dict.get(key)
                        if value is not None:
                            row.append(value)
                        else:
                            default_value = key_metadata.get("default", "")
                            row.append(default_value)
                
                writer.writerow(row)
        
        print(f"[INFO] Exported {len(export_data)} records for phase '{phase}' to {csv_file_path}")
        
        self._export_grouped_by_category(phase, export_data)
        
        return

    def _export_grouped_by_category(self, phase, export_data):
        """
        Export aggregated data grouped by category.
        
        Args:
            phase: The phase being exported
            export_data: List of tuples (app_name, script_id, phase_data, entry_data)
        """
        import csv
        import os
        from collections import defaultdict
        
        if not export_data:
            print(f"[INFO] No data to export for grouped category in phase '{phase}'.")
            return
        
        if not hasattr(self, 'app_to_category'):
            self.app_to_category = {}
        
        if self.metadata is None or self.statistics_output_path is None:
            print(f"[ERROR] Missing metadata or output path. Cannot export grouped data.")
            return
        
        # Group data
        category_data = defaultdict(list)
        
        for app_name, script_id, phase_data, entry_data in export_data:
            category = self.app_to_category.get(app_name, "Unknown")
            
            data_dict = phase_data.get("data", {})
            calculated_metrics = self._calculate_metrics(phase, data_dict, entry_data)
            
            entry_values = {}
            phase_keys = list(self.metadata["keys"][phase].keys())
            
            for key in phase_keys:
                key_metadata = self.metadata["keys"][phase][key]
                
                if key_metadata.get("is_caculated", False):
                    if key in calculated_metrics:
                        value = calculated_metrics[key]
                        # Only include numeric values for averaging
                        if isinstance(value, (int, float)):
                            entry_values[key] = value
                else:
                    value = data_dict.get(key)
                    # Only include numeric values for averaging
                    if isinstance(value, (int, float)):
                        entry_values[key] = value
            
            category_data[category].append(entry_values)
        
        category_averages = {}
        
        for category, entries in category_data.items():
            if not entries:
                continue
                
            all_keys = set()
            for entry in entries:
                all_keys.update(entry.keys())
            
            averages = {}
            for key in all_keys:
                values = [entry[key] for entry in entries if key in entry and entry[key] is not None]
                if values:
                    averages[key] = sum(values) / len(values)
                else:
                    # Use default value from metadata
                    if key in self.metadata["keys"][phase]:
                        default_value = self.metadata["keys"][phase][key].get("default", "")
                        if isinstance(default_value, (int, float)):
                            averages[key] = default_value
                        else:
                            averages[key] = "N/A"
                    else:
                        averages[key] = "N/A"
            
            category_averages[category] = {
                "count": len(entries),
                "averages": averages
            }
        
        grouped_csv_file_path = os.path.join(self.statistics_output_path, f"results_{phase}_grouped.csv")
        
        phase_keys = list(self.metadata["keys"][phase].keys())
        headers = ["category", "count"] + phase_keys
        
        with open(grouped_csv_file_path, "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            
            writer.writerow(headers)
            
            for category in sorted(category_averages.keys()):
                category_info = category_averages[category]
                row = [category, category_info["count"]]
                
                for key in phase_keys:
                    avg_value = category_info["averages"].get(key, "N/A")
                    row.append(avg_value)
                
                writer.writerow(row)
        
        print(f"[INFO] Exported {len(category_averages)} categories for phase '{phase}' to {grouped_csv_file_path}")


if __name__ == "__main__":
    print("=== Testing Logger with New Features ===")
    
    logger = Logger("/Volumes/volume2/Documents/GUIMut/experiments/v6/guimut_clean_code/GUIMut/config.yaml")

    logger.calculate_coverage_stats("ca.rmen.android.poetassistant.test", "script0", "modeling")
    
    # print("\n1. Testing with valid app names from metadata:")
    # # Test with valid apps from different categories
    # logger.log("com.zola.bmi", "script1", "exp_t", 23.0, "modeling")  # Lifestyle
    # logger.log("com.zola.bmi", "script1", "exp_ep", 5, "modeling")
    # logger.log("com.zola.bmi", "script1", "cl", 30, "modeling")
    # logger.log("com.zola.bmi", "script1", "ucl", 20, "modeling")
    
    # logger.log("remix.myplayer.debug", "script1", "exp_t", 150.0, "modeling")  # Media Player
    # logger.log("remix.myplayer.debug", "script1", "exp_ep", 6, "modeling")
    # logger.log("remix.myplayer.debug", "script1", "cl", 40, "modeling")
    # logger.log("remix.myplayer.debug", "script1", "ucl", 10, "modeling")
    
    # logger.log("de.blinkt.openvpn", "script1", "exp_t", 200.0, "modeling")  # Utilities
    # logger.log("de.blinkt.openvpn", "script1", "exp_ep", 8, "modeling")
    # logger.log("de.blinkt.openvpn", "script1", "cl", 25, "modeling")
    # logger.log("de.blinkt.openvpn", "script1", "ucl", 15, "modeling")
    
    # logger.log("org.ligi.passandroid", "script1", "exp_t", 180.0, "modeling")  # Utilities
    # logger.log("org.ligi.passandroid", "script1", "exp_ep", 9, "modeling")
    # logger.log("org.ligi.passandroid", "script1", "cl", 35, "modeling")
    # logger.log("org.ligi.passandroid", "script1", "ucl", 5, "modeling")
    
    # print("\n2. Testing app validation - invalid app name:")
    # # This should show an error
    # logger.log("invalid_app_name", "script1", "exp_t", 50.0, "modeling")
    
    # print("\n3. Testing division by zero cases:")
    # # Test division by zero for exp_st and cc
    # logger.log("cn.super12138.todo", "script1", "exp_t", 90.0, "modeling")  # Notes
    # logger.log("cn.super12138.todo", "script1", "exp_ep", 0, "modeling")  # Should cause exp_st = N/A
    # logger.log("cn.super12138.todo", "script1", "cl", 0, "modeling")
    # logger.log("cn.super12138.todo", "script1", "ucl", 0, "modeling")  # Should cause cc = N/A
    
    # print("\n4. Testing mutation phase with vr calculation:")
    # logger.log("com.zola.bmi", "script1", "gen_cnt", 80, "mutation")
    # logger.log("com.zola.bmi", "script1", "mut_cnt", 100, "mutation")  # vr = 0.8
    # logger.log("com.zola.bmi", "script1", "mut_t", 50.0, "mutation")
    # logger.log("com.zola.bmi", "script1", "steps", "[5, 5, 6]", "mutation")
    
    # # Test division by zero in mutation
    # logger.log("remix.myplayer.debug", "script1", "gen_cnt", 60, "mutation")
    # logger.log("remix.myplayer.debug", "script1", "mut_cnt", 0, "mutation")  # vr = N/A
    # logger.log("remix.myplayer.debug", "script1", "mut_t", 30.0, "mutation")
    # logger.log("remix.myplayer.debug", "script1", "steps", "[5, 5, 6]", "mutation")
    
    # print("\n5. Exporting results:")
    # print("- Regular CSV export with calculated metrics")
    # print("- Grouped CSV export by category with averages")
    
    logger.export("modeling")
    
    # print("\n=== Test completed! Check output directory for results ===\n")
    # print("Files generated:")
    # print("- results_modeling.csv (individual app results)")
    # print("- results_modeling_grouped.csv (category averages)")
    # print("- results_mutation.csv (individual app results)")
    # print("- results_mutation_grouped.csv (category averages)")