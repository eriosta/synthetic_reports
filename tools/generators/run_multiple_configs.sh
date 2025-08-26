#!/bin/bash

# Shell script for running multiple SynthRad configurations
# Usage: ./run_multiple_configs.sh [config_file] [--parallel] [--workers N]

set -e

show_usage() {
    echo "Usage: $0 [config_file] [--parallel] [--workers N]"
    echo ""
    echo "Examples:"
    echo "  $0 sample_configs.json"
    echo "  $0 my_configs.json --parallel --workers 4"
    echo ""
    echo "To create a sample config file first:"
    echo "  python scripts/multi_config_generator.py --create-sample"
    exit 1
}

if [ $# -eq 0 ]; then
    show_usage
fi

CONFIG_FILE="$1"
PARALLEL=false
MAX_WORKERS=""

# Parse arguments
shift
while [ $# -gt 0 ]; do
    case "$1" in
        --parallel)
            PARALLEL=true
            shift
            ;;
        --workers)
            MAX_WORKERS="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            ;;
    esac
done

echo "Running multiple SynthRad configurations..."
echo "Config file: $CONFIG_FILE"
echo "Parallel: $PARALLEL"
if [ -n "$MAX_WORKERS" ]; then
    echo "Max workers: $MAX_WORKERS"
fi
echo ""

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Configuration file '$CONFIG_FILE' not found!"
    exit 1
fi

# Run the generator
if [ "$PARALLEL" = true ]; then
    if [ -n "$MAX_WORKERS" ]; then
        python scripts/multi_config_generator.py --configs "$CONFIG_FILE" --parallel --max-workers "$MAX_WORKERS"
    else
        python scripts/multi_config_generator.py --configs "$CONFIG_FILE" --parallel
    fi
else
    python scripts/multi_config_generator.py --configs "$CONFIG_FILE"
fi

echo ""
echo "Done! Check the output directories for generated reports."
