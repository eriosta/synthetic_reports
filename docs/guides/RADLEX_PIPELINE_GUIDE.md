# RadLex Pipeline Integration Guide

This guide explains how to use RadLex integration in your core synthetic report generation pipeline with different configuration distributions.

## Overview

The RadLex integration has been added to your core generator pipeline, allowing you to:

- **Control RadLex enhancement per case** using configuration distributions
- **Mix different enhancement levels** across your generated reports
- **Maintain compatibility** with all existing features (follow-up, JSONL, etc.)
- **Fine-tune enhancement** based on your specific needs

## Quick Start

### Basic Usage

```bash
# Generate reports with standard RadLex enhancement
python -m synthrad --n 10 --radlex-dist standard:1.0 --out ./reports

# Generate reports with mixed RadLex configurations
python -m synthrad --n 10 --radlex-dist minimal:0.2,standard:0.5,aggressive:0.2,conservative:0.1 --out ./mixed_reports
```

### RadLex Configuration Options

The integration provides four predefined RadLex configurations:

- **`minimal`**: Basic RadLex access without text enhancement
- **`standard`**: Balanced enhancement (default)
- **`aggressive`**: Maximum enhancement (up to 50% of text)
- **`conservative`**: Minimal enhancement (up to 10% of text)

## Distribution Control

### Single Configuration

Use one configuration for all cases:

```bash
# All cases use conservative enhancement
python -m synthrad --n 10 --radlex-dist conservative:1.0 --out ./conservative_reports

# All cases use aggressive enhancement
python -m synthrad --n 10 --radlex-dist aggressive:1.0 --out ./aggressive_reports
```

### Mixed Distributions

Specify proportions of different configurations:

```bash
# 60% standard, 30% aggressive, 10% conservative
python -m synthrad --n 10 --radlex-dist standard:0.6,aggressive:0.3,conservative:0.1 --out ./mixed_reports

# 20% minimal, 50% standard, 20% aggressive, 10% conservative
python -m synthrad --n 10 --radlex-dist minimal:0.2,standard:0.5,aggressive:0.2,conservative:0.1 --out ./balanced_reports
```

### Distribution Examples

Here are some common distribution patterns:

```bash
# Mostly basic (for conservative enhancement)
python -m synthrad --n 10 --radlex-dist minimal:0.4,conservative:0.4,standard:0.2 --out ./basic_reports

# Mostly enhanced (for maximum terminology enhancement)
python -m synthrad --n 10 --radlex-dist standard:0.6,aggressive:0.3,conservative:0.1 --out ./enhanced_reports

# Balanced mix (for variety)
python -m synthrad --n 10 --radlex-dist minimal:0.2,standard:0.5,aggressive:0.2,conservative:0.1 --out ./balanced_reports
```

## Integration with Other Features

### Follow-up Cases

RadLex enhancement works with follow-up case generation:

```bash
# Generate follow-up cases with mixed RadLex configurations
python -m synthrad --n 5 --follow-up --studies-per-patient 4 --radlex-dist standard:0.6,aggressive:0.4 --out ./followup_reports
```

### JSONL Output

RadLex enhancement is compatible with JSONL output:

```bash
# Generate JSONL with RadLex enhancement
python -m synthrad --n 5 --studies-per-patient 3 --radlex-dist minimal:0.3,standard:0.4,aggressive:0.3 --jsonl cohort.jsonl --out ./jsonl_reports
```

### Stage and Response Distributions

RadLex distributions work alongside existing distributions:

```bash
# Combine with stage and response distributions
python -m synthrad --n 10 \
  --stage-dist "I:0.2,II:0.25,III:0.35,IV:0.2" \
  --response-dist "CR:0.1,PR:0.3,SD:0.4,PD:0.2" \
  --radlex-dist "standard:0.6,aggressive:0.3,conservative:0.1" \
  --out ./complex_reports
```

## Configuration Details

### How Distributions Work

1. **Per-Case Selection**: Each case gets a RadLex configuration selected based on the distribution
2. **Random Selection**: Configurations are selected using weighted random sampling
3. **Normalization**: Distributions are automatically normalized to sum to 1.0
4. **Fallback**: If RadLex is unavailable, cases fall back to standard terminology

### Configuration Parameters

Each RadLex configuration includes:

- **`enhance_terminology`**: Whether to enhance medical terminology
- **`enhance_artifacts`**: Whether to enhance artifact descriptions
- **`enhance_anatomy`**: Whether to enhance anatomical descriptions
- **`auto_enhance_reports`**: Whether to automatically enhance generated reports
- **`max_enhancement_ratio`**: Maximum percentage of text to enhance
- **`preserve_original_terms`**: Whether to preserve original terms

### Predefined Configurations

```python
# Minimal configuration
minimal = {
    "enhance_terminology": False,
    "enhance_artifacts": False,
    "enhance_anatomy": False,
    "auto_enhance_reports": False
}

# Standard configuration
standard = {
    "enhance_terminology": True,
    "enhance_artifacts": True,
    "enhance_anatomy": True,
    "auto_enhance_reports": True,
    "max_enhancement_ratio": 0.3
}

# Aggressive configuration
aggressive = {
    "enhance_terminology": True,
    "enhance_artifacts": True,
    "enhance_anatomy": True,
    "auto_enhance_reports": True,
    "max_enhancement_ratio": 0.5
}

# Conservative configuration
conservative = {
    "enhance_terminology": True,
    "enhance_artifacts": False,
    "enhance_anatomy": False,
    "auto_enhance_reports": True,
    "max_enhancement_ratio": 0.1
}
```

## Examples

### Example 1: Conservative Enhancement

Generate reports with minimal RadLex enhancement:

```bash
python -m synthrad --n 5 --radlex-dist conservative:1.0 --out ./conservative_reports
```

**Result**: Reports use basic RadLex terminology with minimal text enhancement.

### Example 2: Mixed Enhancement

Generate reports with a mix of enhancement levels:

```bash
python -m synthrad --n 10 --radlex-dist minimal:0.2,standard:0.5,aggressive:0.2,conservative:0.1 --out ./mixed_reports
```

**Result**: 
- 20% of cases use minimal enhancement
- 50% of cases use standard enhancement
- 20% of cases use aggressive enhancement
- 10% of cases use conservative enhancement

### Example 3: Follow-up with Enhancement

Generate follow-up cases with enhanced terminology:

```bash
python -m synthrad --n 3 --follow-up --studies-per-patient 4 --radlex-dist standard:0.6,aggressive:0.4 --out ./followup_enhanced
```

**Result**: Each case in the timeline gets enhanced terminology, with 60% standard and 40% aggressive enhancement.

## Performance Considerations

### API Usage

- **Caching**: RadLex concepts are cached to reduce API calls
- **Rate Limiting**: BioPortal has rate limits for free accounts
- **Fallback**: System gracefully falls back to standard terminology if RadLex unavailable

### Enhancement Overhead

- **Minimal**: No additional processing overhead
- **Conservative**: Low overhead, minimal text changes
- **Standard**: Moderate overhead, balanced enhancement
- **Aggressive**: Higher overhead, maximum enhancement

## Troubleshooting

### Common Issues

1. **Missing API Key**
   ```
   Warning: RadLex unavailable, using standard lexicons
   ```
   Solution: Set `BIOPORTAL_API_KEY` environment variable

2. **Invalid Distribution**
   ```
   ValueError: Unknown RadLex config: invalid_name
   ```
   Solution: Use valid config names: `minimal`, `standard`, `aggressive`, `conservative`

3. **Distribution Sum Error**
   ```
   ValueError: RadLex distribution must sum > 0
   ```
   Solution: Ensure distribution values are positive numbers

### Debug Mode

Enable debug logging to see RadLex processing:

```bash
export PYTHONPATH=./src
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from synthrad.generator import main
main()
"
```

## Best Practices

### 1. Start Conservative

Begin with conservative or minimal enhancement:

```bash
python -m synthrad --n 5 --radlex-dist conservative:1.0 --out ./test_reports
```

### 2. Test Different Distributions

Experiment with different distributions to find the right balance:

```bash
# Test minimal enhancement
python -m synthrad --n 3 --radlex-dist minimal:1.0 --out ./test_minimal

# Test standard enhancement
python -m synthrad --n 3 --radlex-dist standard:1.0 --out ./test_standard

# Test mixed enhancement
python -m synthrad --n 3 --radlex-dist minimal:0.3,standard:0.4,aggressive:0.3 --out ./test_mixed
```

### 3. Monitor API Usage

Watch your BioPortal API usage, especially with aggressive enhancement:

```bash
# Use conservative enhancement for large batches
python -m synthrad --n 100 --radlex-dist conservative:0.8,standard:0.2 --out ./large_batch
```

### 4. Validate Results

Have medical professionals review enhanced reports to ensure appropriateness:

```bash
# Generate a small validation set
python -m synthrad --n 10 --radlex-dist aggressive:1.0 --out ./validation_set
```

## Advanced Usage

### Custom Configurations

For advanced users, you can create custom RadLex configurations:

```python
from synthrad.radlex_config import RadLexConfig

# Create custom configuration
custom_config = RadLexConfig(
    enabled=True,
    enhance_terminology=True,
    enhance_artifacts=False,
    enhance_anatomy=True,
    auto_enhance_reports=True,
    max_enhancement_ratio=0.25
)

# Save to file
custom_config.to_json("custom_radlex_config.json")
```

### Integration with Existing Workflows

The RadLex integration is designed to work seamlessly with existing workflows:

```bash
# Your existing command
python -m synthrad --n 10 --stage-dist "I:0.2,II:0.25,III:0.35,IV:0.2" --out ./reports

# With RadLex enhancement
python -m synthrad --n 10 --stage-dist "I:0.2,II:0.25,III:0.35,IV:0.2" --radlex-dist standard:1.0 --out ./enhanced_reports
```

## Summary

The RadLex pipeline integration provides:

- **Flexible Enhancement**: Control enhancement levels per case
- **Distribution Control**: Mix different enhancement configurations
- **Full Compatibility**: Works with all existing generator features
- **Performance Optimized**: Caching and fallback mechanisms
- **Easy Configuration**: Simple command-line interface

Start with conservative enhancement and gradually increase based on your needs and validation results.

