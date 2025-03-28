# GUIMut

GUIMut is a mobile test generation tool that automatically generates diverse test cases from existing test scripts. It explores Android app GUIs, builds transition graphs, and generates mutated test cases that follow metamorphic relations.

## Overview

GUIMut works in two main phases:

1. **GUI Exploration**: Automatically explores the GUI of an Android app to build a state transition graph
2. **Path Mutation**: Generates new test cases by mutating execution paths using metamorphic relations (MRs)

## Project Structure

```
GUIMut/
├── device_infrastructure/      # Android device management & Appium integration
│   ├── device_manager.py       # Device control and app management
│   ├── env_manager.py          # Environment setup
│   └── actions/                # Device actions (screenshots, input, etc.)
├── gui_exploration/            # GUI exploration engine
│   ├── gui_explorer.py         # Main explorer
│   └── utils/                  # Exploration utilities
├── transition_graph/           # State transition graph management
│   ├── manager/                # Graph and state managers
│   ├── nodes/                  # Graph node definitions
│   └── events/                 # Event definitions
├── mutator/                    # Test mutation engine
│   ├── mutator.py              # Main mutator
│   └── metamorphic_relations.py # MR implementations
├── path_mapping/               # Path and execution flow mapping
├── verifier/                   # Test verification
├── statistic/                  # Statistics collection
├── main.py                     # Entry point
├── requirements.txt            # Python dependencies
└── config.example.yaml         # Configuration template
```

## Quick Start

### Prerequisites

- Python 3.9+
- Android SDK with emulator (or connected device)
- Appium
- Java Development Kit (JDK) for coverage analysis (optional)

### 1. Installation

Clone the repository and install dependencies:

```bash
git clone <repository-url>
cd GUIMut
pip install -r requirements.txt
```

You need to have Appium server installed. Read the [Appium installation guide](https://appium.io/docs/en/latest/quickstart/install/) for detailed instructions.

### 2. Configure Your Setup

Copy the example config and customize it:

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml` with your environment settings.

### 3. Prepare Your Test Scripts

Create your input test scripts in the format:
```
script_dir/
├── ActivityName@package.name/
│   ├── test_case1.py
│   ├── test_case2.py
│   └── ...
└── AnotherActivity@package.name/
    └── test_case1.py
```

Test scripts should be written in Python using the Appium client. You also need to ensure that the scripts follow the expected structure for GUIMut to parse them correctly. We recommend reviewing the example test script provided in the `path_mapping/example_script` directory.

### 4. Run GUIMut

#### Run Full Pipeline (Explore + Mutate)

```bash
python main.py -f config.yaml
```

#### Run GUI Exploration Only

```bash
python main.py -f config.yaml -e
```

#### Run Path Mutation Only

```bash
python main.py -f config.yaml -m
```

### 5. Output Structure

After running, check your output directory:

```
output_folder/
├── app_name1/
│   ├── mutated_test_cases/
│   │   ├── test_case1/
│   │   │   ├── mutated_test_case1.py
│   │   │   ├── mutated_test_case2.py
│   │   │   └── ...
│   │   └── test_case2/
│   ├── transition_graph/        # State transition graph data
│   ├── screenshots/             # Captured screenshots
│   ├── logs/                    # Execution logs
│   └── coverage_data/           # Coverage information (if enabled)
└── app_name2/
    └── ...
```

## License

This work is licensed under the MIT License. See LICENSE file for details.

## References

- [Appium Documentation](http://appium.io/)
- [GUI Testing](https://en.wikipedia.org/wiki/Graphical_user_interface_testing)
- [Metamorphic Testing](https://en.wikipedia.org/wiki/Metamorphic_testing)
