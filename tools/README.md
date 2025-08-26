# Tools

This directory contains all utility tools and scripts for SynthRad.

## Directory Structure

```
tools/
├── builders/         # Configuration building tools
│   └── config_builder.py
├── generators/       # Report generation tools
│   ├── multi_config_generator.py
│   ├── generate_reports.py
│   ├── run_multiple_configs.bat
│   └── run_multiple_configs.sh
├── utils/            # Utility modules
│   └── config_manager.py
└── README.md         # This file
```

## Tools Overview

### Builders (`builders/`)
Tools for creating and managing configurations:
- **config_builder.py** - Interactive configuration builder

### Generators (`generators/`)
Tools for generating synthetic reports:
- **multi_config_generator.py** - Main multi-configuration generator
- **generate_reports.py** - Simple report generator
- **run_multiple_configs.bat** - Windows batch script
- **run_multiple_configs.sh** - Unix/Linux shell script

### Utils (`utils/`)
Core utility modules:
- **config_manager.py** - Configuration management system

## Quick Start

```bash
# Create sample configurations
python tools/builders/config_builder.py

# Run multiple configurations
python tools/generators/multi_config_generator.py --configs configs/samples/sample_configs.json

# Windows users
tools\generators\run_multiple_configs.bat configs\samples\sample_configs.json

# Unix/Linux users
./tools/generators/run_multiple_configs.sh configs/samples/sample_configs.json
```

## Tool Descriptions

### config_builder.py
Interactive tool for creating SynthRad configurations with guided prompts and validation.

### multi_config_generator.py
Main tool for running multiple SynthRad configurations in parallel or sequentially.

### config_manager.py
Core module providing clean, type-safe configuration management with validation.
