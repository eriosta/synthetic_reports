# Configuration Files

This directory contains all SynthRad configuration files organized by type.

## Directory Structure

```
configs/
├── samples/          # Sample configuration files
│   ├── sample_configs.json
│   └── sample_configs.yaml
├── research/         # Research-focused configurations
├── custom/           # Your custom configurations
└── README.md         # This file
```

## Configuration Types

### Samples (`samples/`)
Pre-built configuration files demonstrating different SynthRad features:
- **sample_configs.json** - JSON format sample configurations
- **sample_configs.yaml** - YAML format sample configurations

### Research (`research/`)
Configurations designed for research and clinical trial simulation:
- Clinical trial arm configurations
- Follow-up interval studies
- Lobe-specific studies

### Custom (`custom/`)
Place your own custom configurations here.

## Usage

```bash
# Run sample configurations
python tools/generators/multi_config_generator.py --configs configs/samples/sample_configs.json

# Run research configurations
python tools/generators/multi_config_generator.py --configs configs/research/research_configs.json

# Run your custom configurations
python tools/generators/multi_config_generator.py --configs configs/custom/my_configs.json
```

## Creating New Configurations

Use the interactive configuration builder:
```bash
python tools/builders/config_builder.py
```

Or create configuration files manually using the format shown in the sample files.
