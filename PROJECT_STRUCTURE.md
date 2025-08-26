# SynthRad Project Structure

This document provides an overview of the organized SynthRad project structure.

## Directory Organization

```
synthetic_reports/
├── README.md                    # Main project documentation
├── PROJECT_STRUCTURE.md         # This file
├── pyproject.toml              # Project configuration
├── .gitignore                  # Git ignore rules
│
├── src/                        # Source code
│   ├── synthrad/              # Main SynthRad package
│   │   ├── __init__.py
│   │   ├── __main__.py
│   │   ├── generator.py
│   │   ├── lexicons.py
│   │   ├── radlex_config.py
│   │   ├── radlex_lexicons.py
│   │   ├── radlex_service.py
│   │   └── schema.py
│   ├── radlex.py              # RadLex integration
│   └── synthrad.egg-info/     # Package metadata
│
├── configs/                    # Configuration files
│   ├── samples/               # Sample configurations
│   │   ├── sample_configs.json
│   │   └── sample_configs.yaml
│   ├── research/              # Research configurations
│   ├── custom/                # Custom configurations
│   └── README.md              # Configuration documentation
│
├── tools/                      # Utility tools and scripts
│   ├── builders/              # Configuration building tools
│   │   └── config_builder.py
│   ├── generators/            # Report generation tools
│   │   ├── multi_config_generator.py
│   │   ├── generate_reports.py
│   │   ├── run_multiple_configs.bat
│   │   └── run_multiple_configs.sh
│   ├── utils/                 # Utility modules
│   │   └── config_manager.py
│   └── README.md              # Tools documentation
│
├── docs/                       # Documentation
│   ├── guides/                # User guides and tutorials
│   │   ├── README.md
│   │   ├── RADLEX_INTEGRATION.md
│   │   └── RADLEX_PIPELINE_GUIDE.md
│   ├── api/                   # API documentation
│   ├── examples/              # Documentation examples
│   └── README.md              # Documentation overview
│
├── examples/                   # Example scripts
│   ├── radlex_example.py
│   ├── radlex_pipeline_demo.py
│   └── README.md
│
├── tests/                      # Test files
│   ├── test_basic.py
│   └── test_radlex_integration.py
│
├── radlex_cache/              # RadLex cache directory
└── out/                       # Generated output (created when running)
```

## Key Directories Explained

### `src/` - Source Code
Contains the main SynthRad package and core functionality.

### `configs/` - Configuration Management
- **samples/** - Pre-built configuration examples
- **research/** - Research-focused configurations
- **custom/** - User-created configurations

### `tools/` - Utility Tools
- **builders/** - Tools for creating configurations
- **generators/** - Tools for generating reports
- **utils/** - Core utility modules

### `docs/` - Documentation
- **guides/** - User guides and tutorials
- **api/** - API documentation
- **examples/** - Documentation examples

### `examples/` - Code Examples
Working examples demonstrating SynthRad features.

## Quick Navigation

### For New Users
1. Start with `README.md` (project root)
2. Check `configs/samples/` for configuration examples
3. Run `tools/builders/config_builder.py` to create configurations
4. Use `tools/generators/multi_config_generator.py` to run configurations

### For Developers
1. Core code in `src/synthrad/`
2. Tests in `tests/`
3. Configuration system in `tools/utils/config_manager.py`
4. Examples in `examples/`

### For Documentation
1. Main docs in `docs/guides/`
2. API docs in `docs/api/`
3. Examples in `docs/examples/`

## File Naming Conventions

- **Configuration files**: `*_configs.json` or `*_configs.yaml`
- **Tools**: Descriptive names with `.py` extension
- **Documentation**: Clear, descriptive names with `.md` extension
- **Examples**: Descriptive names with `.py` extension

## Best Practices

1. **Keep configurations organized** in appropriate subdirectories
2. **Use the tools** in `tools/` rather than modifying files directly
3. **Follow the documentation** in `docs/` for best practices
4. **Test your configurations** before running large batches
5. **Use descriptive names** for custom configurations and outputs
