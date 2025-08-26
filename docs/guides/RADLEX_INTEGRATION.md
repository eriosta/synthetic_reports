# RadLex Integration Guide

This guide explains how to integrate RadLex ontology into your synthetic radiology reports to add realistic medical terminology.

## Overview

RadLex is a comprehensive lexicon of radiological terms that provides standardized medical terminology. This integration allows you to:

- Enhance synthetic reports with realistic medical terminology
- Use standardized RadLex concepts for findings, anatomy, and artifacts
- Cache RadLex concepts for improved performance
- Configure the level of enhancement based on your needs

## Quick Start

### 1. Get a BioPortal API Key

1. Visit [BioPortal](https://bioportal.bioontology.org/)
2. Create a free account
3. Generate an API key
4. Set the environment variable:
   ```bash
   export BIOPORTAL_API_KEY="your_api_key_here"
   ```

### 2. Install Dependencies

The integration requires the `requests` library, which is already added to `pyproject.toml`:

```bash
pip install -e .
```

### 3. Basic Usage

```python
from synthrad.radlex_lexicons import get_radlex_lexicons

# Get enhanced lexicons
lexicons = get_radlex_lexicons()

# Enhance a term
enhanced_term = lexicons.get_lung_finding_term("nodule")
print(enhanced_term)  # "Pulmonary nodule" or "Solitary pulmonary nodule"

# Enhance text
original_text = "There is a nodule in the right upper lobe."
enhanced_text = lexicons.enhance_text_with_radlex(original_text)
print(enhanced_text)  # "There is a Pulmonary nodule in the right upper lobe."
```

## Configuration

### Environment Variables

You can configure RadLex integration using environment variables:

```bash
# Core settings
export BIOPORTAL_API_KEY="your_api_key"
export RADLEX_ENABLED="true"
export RADLEX_CACHE_FILE="./radlex_cache/concepts.json"

# Enhancement settings
export RADLEX_ENHANCE_TERMINOLOGY="true"
export RADLEX_ENHANCE_ARTIFACTS="true"
export RADLEX_ENHANCE_ANATOMY="true"
export RADLEX_AUTO_ENHANCE="true"

# Performance settings
export RADLEX_CACHE_ENABLED="true"
export RADLEX_CACHE_DIR="./radlex_cache"
export RADLEX_TIMEOUT="30"
export RADLEX_MAX_RETRIES="3"
```

### JSON Configuration

Create a configuration file for more control:

```python
from synthrad.radlex_config import create_config_template, get_config

# Create a template
create_config_template("radlex_config.json", "standard")

# Load configuration
config = get_config(config_file="radlex_config.json")
```

Example configuration file (`radlex_config.json`):

```json
{
  "enabled": true,
  "api_key": "your_bioportal_api_key_here",
  "cache_file": "./radlex_cache/concepts.json",
  "enhance_terminology": true,
  "enhance_artifacts": true,
  "enhance_anatomy": true,
  "auto_enhance_reports": true,
  "preserve_original_terms": false,
  "max_enhancement_ratio": 0.3,
  "enable_caching": true,
  "cache_dir": "./radlex_cache",
  "request_timeout": 30,
  "max_retries": 3,
  "concept_categories": [
    "lung_findings",
    "lymph_nodes",
    "pleura",
    "mediastinum",
    "artifacts"
  ]
}
```

### Predefined Configurations

The integration provides several predefined configurations:

- **minimal**: Basic RadLex access without text enhancement
- **standard**: Balanced enhancement (default)
- **aggressive**: Maximum enhancement (up to 50% of text)
- **conservative**: Minimal enhancement (up to 10% of text)

```python
from synthrad.radlex_config import get_config

# Use predefined config
config = get_config(config_name="conservative")
```

## Integration with Report Generator

### Option 1: Enhance Existing Reports

Modify your report generation to include RadLex enhancement:

```python
from synthrad.radlex_lexicons import get_radlex_lexicons

def generate_enhanced_report(case_data):
    # Generate report as usual
    report_text = generate_report(case_data)
    
    # Enhance with RadLex
    lexicons = get_radlex_lexicons()
    enhanced_report = lexicons.enhance_text_with_radlex(report_text)
    
    return enhanced_report
```

### Option 2: Use Enhanced Lexicons

Replace your existing lexicons with RadLex-enhanced versions:

```python
from synthrad.radlex_lexicons import get_radlex_lexicons

def generate_findings_section(case_data):
    lexicons = get_radlex_lexicons()
    
    # Use enhanced terms
    nodule_term = lexicons.get_lung_finding_term("nodule")
    lymph_term = lexicons.get_lymph_node_term("4R", 15)
    artifact_term = lexicons.get_artifact_term("motion")
    
    findings = f"""
    FINDINGS:
    There is a 25mm {nodule_term} in the right upper lobe.
    {lymph_term} is present.
    {artifact_term} limits evaluation in some areas.
    """
    
    return findings
```

### Option 3: Direct API Integration

Use the RadLex service directly for custom enhancements:

```python
from synthrad.radlex_service import get_radlex_service

def enhance_specific_terms(text, terms_to_enhance):
    service = get_radlex_service()
    enhanced_text = text
    
    for term in terms_to_enhance:
        concept = service.get_concept_by_text(term)
        if concept:
            enhanced_text = enhanced_text.replace(term, concept["class_label"])
    
    return enhanced_text
```

## Advanced Features

### Concept Search

Search for RadLex concepts programmatically:

```python
from synthrad.radlex_service import get_radlex_service

service = get_radlex_service()
concepts = service.search_concepts("pulmonary nodule", max_results=5)

for concept in concepts:
    print(f"- {concept['label']}")
    print(f"  Definition: {concept.get('definition', 'N/A')}")
    print(f"  IRI: {concept['iri']}")
```

### Synonym Access

Get synonyms for RadLex concepts:

```python
from synthrad.radlex_lexicons import get_radlex_lexicons

lexicons = get_radlex_lexicons()
synonyms = lexicons.get_radlex_synonyms("pulmonary nodule")
print(f"Synonyms: {synonyms}")
```

### Custom Caching

Control caching behavior:

```python
from synthrad.radlex_service import get_radlex_service

# Use custom cache file
service = get_radlex_service(cache_file="./my_radlex_cache.json")

# The cache will be automatically saved and loaded
```

## Performance Considerations

### Caching

- RadLex concepts are automatically cached to reduce API calls
- Cache files are saved as JSON for persistence
- Set `RADLEX_CACHE_ENABLED=false` to disable caching

### Rate Limiting

- **Built-in Rate Limiting**: The system includes automatic rate limiting to respect BioPortal API limits
- **Default Settings**: 1 call/second, 60 calls/minute (free tier)
- **Configurable**: Can be adjusted via environment variables or code
- **Thread-Safe**: Automatic waiting prevents hitting API limits

#### Rate Limiting Configuration

```python
# Environment variables
export RADLEX_RATE_LIMIT_PER_SECOND=1.0
export RADLEX_RATE_LIMIT_PER_MINUTE=60

# Code configuration
from synthrad.radlex_service import RadLexService
service = RadLexService(
    rate_limit_per_second=1.0,
    rate_limit_per_minute=60
)
```

#### Rate Limiting Best Practices

- **Free Tier**: Use default settings (1/sec, 60/min)
- **Development**: Can use faster limits for testing
- **Production**: Use conservative limits to avoid API blocks
- **Batch Processing**: Use very conservative limits (0.5/sec, 30/min)

### Offline Mode

If you don't have an API key or want to work offline:

```python
# Disable RadLex
lexicons = get_radlex_lexicons(use_radlex=False)

# Or use environment variable
export RADLEX_ENABLED="false"
```

## Error Handling

The integration includes robust error handling:

```python
from synthrad.radlex_lexicons import get_radlex_lexicons

try:
    lexicons = get_radlex_lexicons()
    enhanced_text = lexicons.enhance_text_with_radlex(original_text)
except Exception as e:
    print(f"RadLex enhancement failed: {e}")
    # Fall back to original text
    enhanced_text = original_text
```

## Examples

Run the example script to see RadLex integration in action:

```bash
python scripts/radlex_example.py
```

This will demonstrate:
- Text annotation with RadLex concepts
- Enhanced lexicon usage
- Text enhancement
- Configuration options
- Concept searching

## Troubleshooting

### Common Issues

1. **Missing API Key**
   ```
   RuntimeError: Missing BIOPORTAL_API_KEY environment variable
   ```
   Solution: Set the `BIOPORTAL_API_KEY` environment variable

2. **API Rate Limiting**
   ```
   requests.exceptions.HTTPError: 429 Too Many Requests
   ```
   Solution: Wait and retry, or upgrade to a paid API key

3. **Network Issues**
   ```
   requests.exceptions.ConnectionError
   ```
   Solution: Check internet connection and try again

4. **Cache Issues**
   ```
   json.JSONDecodeError
   ```
   Solution: Delete the cache file and restart

### Debug Mode

Enable debug logging to see detailed information:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Best Practices

1. **Start Conservative**: Begin with minimal enhancement and increase gradually
2. **Test Thoroughly**: Verify that enhanced terms are appropriate for your use case
3. **Monitor Performance**: Watch API usage and cache effectiveness
4. **Backup Original**: Keep original text as fallback in case of issues
5. **Validate Results**: Have medical professionals review enhanced reports

## API Reference

### RadLexService

- `annotate_text(text, include_metadata=True)`: Annotate text with RadLex concepts
- `get_concept_by_text(text)`: Get specific concept by text
- `search_concepts(query, max_results=10)`: Search for concepts
- `get_synonyms(concept_iri)`: Get synonyms for a concept

### RadLexEnhancedLexicons

- `get_lung_finding_term(finding_type, fallback=None)`: Get enhanced lung finding term
- `get_lymph_node_term(station, size_mm)`: Get enhanced lymph node description
- `get_pleural_term(finding_type, fallback=None)`: Get enhanced pleural term
- `get_artifact_term(artifact_type)`: Get enhanced artifact term
- `enhance_text_with_radlex(text)`: Enhance entire text with RadLex concepts
- `get_radlex_synonyms(term)`: Get synonyms for a term
- `search_radlex_concepts(query, max_results=5)`: Search for concepts

### RadLexConfig

- `enabled`: Enable/disable RadLex integration
- `enhance_terminology`: Enhance medical terminology
- `enhance_artifacts`: Enhance artifact descriptions
- `enhance_anatomy`: Enhance anatomical descriptions
- `auto_enhance_reports`: Automatically enhance generated reports
- `max_enhancement_ratio`: Maximum percentage of text to enhance
- `enable_caching`: Enable concept caching
- `cache_file`: Path to cache file
