# Scripts Directory

This directory contains various scripts for testing, examples, and demonstrations of the synthetic radiology report generator.

## Directory Structure

```
scripts/
├── README.md                    # This file
├── examples/                    # Example scripts
│   └── radlex_example.py       # Basic RadLex integration examples
├── demos/                       # Demonstration scripts
│   └── radlex_pipeline_demo.py # RadLex pipeline demonstrations
├── tests/                       # Test scripts (moved to tests/ directory)
└── generate_reports.py          # Simple report generation script
```

## Script Categories

### Examples (`examples/`)
- **`radlex_example.py`**: Basic examples of using RadLex service, lexicons, and configuration
- Shows how to annotate text, use enhanced lexicons, and search concepts

### Demos (`demos/`)
- **`radlex_pipeline_demo.py`**: Comprehensive demonstrations of RadLex pipeline integration
- Tests different RadLex distributions and shows usage examples

### Tests (moved to `tests/`)
- **`test_radlex_integration.py`**: Comprehensive test suite for all RadLex functionality
- Includes rate limiting, duplicate findings, pipeline, and basic functionality tests

### Utilities
- **`generate_reports.py`**: Simple script for basic report generation

## Usage

### Run Examples
```bash
# Basic RadLex examples
python scripts/examples/radlex_example.py

# RadLex pipeline demonstrations
python scripts/demos/radlex_pipeline_demo.py
```

### Run Tests
```bash
# Run comprehensive test suite
python tests/test_radlex_integration.py

# Run basic tests
python tests/test_basic.py
```

### Generate Reports
```bash
# Simple report generation
python scripts/generate_reports.py
```

## Notes

- All scripts automatically add the `src/` directory to the Python path
- Scripts check for `BIOPORTAL_API_KEY` environment variable for RadLex functionality
- Test outputs are automatically cleaned up after running
- Examples and demos create output directories for inspection

## Organization Benefits

1. **Clear Separation**: Examples, demos, and tests are clearly separated
2. **Easy Navigation**: Related functionality is grouped together
3. **Maintainable**: Each script has a specific purpose and clear documentation
4. **Reusable**: Scripts can be run independently or as part of larger workflows

