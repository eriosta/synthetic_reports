# Ontology-Focused RadLex Integration

This document describes the enhanced RadLex integration that generates ontology-focused configuration files for each study, following RadLex graph principles and AJCC TNM staging schemas.

## Overview

The new system generates **RadLex-anchored graph JSON** configurations that provide:

- **Ontology compliance**: Each anatomical entity anchored to RadLex RID
- **Graph structure**: Nodes and edges representing relationships
- **Persistent lesion tracking**: Lesion UIDs across timepoints
- **Controlled vocabularies**: Standardized terminology
- **Clinical standards**: RECIST 1.1 and AJCC TNM staging

## Architecture

### Core Components

1. **`RadLexResolver`** - Enhanced resolver with search-first strategy
2. **`OntologyConfigGenerator`** - Generates graph JSON configurations
3. **Enhanced `RadLexAnatomicMapper`** - Uses new resolver for mapping

### Key Features

- **Search-first strategy**: Exact matching before fuzzy search
- **Context-aware resolution**: Uses anatomical context for disambiguation
- **Persistent lesion UIDs**: Enables temporal tracking
- **Graph relationships**: Explicit edges between entities
- **Offline mode**: Works without API access using seeded concepts

## Configuration Structure

Each study generates a configuration file with this structure:

```json
{
  "graph_id": "P0000_t0",
  "patient_id": "P0000",
  "study": {
    "study_id": "P0000_2024-07-27_CT-CAP",
    "modality": "CT",
    "body_regions": ["RID1243"],
    "contrast": true,
    "study_date": "2024-07-27",
    "report_sections": { ... }
  },
  "context": {
    "cancer_type": { "text": "NSCLC", "ncit": "C2926" },
    "timepoint": 0,
    "recist": { ... },
    "staging": { "T": "T1a", "N": "N1", "M": "M0", "stage_group": "IIIA" }
  },
  "nodes": [
    {
      "id": "lesion:primary_RML",
      "type": "lesion",
      "lesion_uid": "L-P0000-RML-001",
      "category": "primary_tumor",
      "status": "active",
      "anatomy": {
        "text": "right middle lobe of lung",
        "radlex": {
          "label": "right middle lobe of lung",
          "rid": "RID13171",
          "iri": "http://radlex.org/RID13171"
        },
        "parents": [ ... ]
      },
      "measurements": [ ... ],
      "attributes": [ ... ],
      "target_status": "target"
    }
  ],
  "edges": [
    {
      "from": "lesion:primary_RML",
      "to": "anatomy:right_middle_lobe_of_lung",
      "relation": "located_in"
    }
  ],
  "provenance": { ... }
}
```

## Usage

### Basic Usage

```python
from synthrad.ontology_config_generator import OntologyConfigGenerator

# Create generator
generator = OntologyConfigGenerator(use_radlex=True)

# Generate config for a study
config = generator.generate_ontology_config(
    case_data=case_data,
    patient_id="P0000",
    study_date="2024-07-27",
    timepoint=0
)

# Save to file
generator.save_ontology_config(config, "output_dir")
```

### Batch Processing

```python
from synthrad.ontology_config_generator import generate_ontology_configs_for_cohort

# Generate configs for entire cohort
config_files = generate_ontology_configs_for_cohort(
    cohort_data=cohort_data,
    output_dir="ontology_configs",
    use_radlex=True
)
```

## Graph Queries

The graph structure enables powerful queries:

```python
# Find all lesions in right lung
right_lung_lesions = [
    node for node in config.nodes 
    if (node.get('type') == 'lesion' and 
        'right' in node.get('anatomy', {}).get('text', ''))
]

# Find all target lesions
target_lesions = [
    node for node in config.nodes 
    if (node.get('type') == 'lesion' and 
        node.get('target_status') == 'target')
]

# Find anatomical hierarchy
anatomical_nodes = [
    node for node in config.nodes 
    if node.get('type') == 'anatomical_region'
]
```

## RadLex Integration

### Resolution Strategy

1. **Cache check** - Check local cache and seed dictionary
2. **Exact search** - Search with `exact_match=true`
3. **Context-boosted query** - Add anatomical context
4. **Best search** - Fallback to top result
5. **Annotator** - Last resort span-based matching

### Seeded Concepts

High-value anatomical concepts are pre-seeded:

```python
seed = {
    "lung": {"label": "lung", "rid": "RID12780"},
    "right middle lobe of lung": {"label": "right middle lobe of lung", "rid": "RID13171"},
    "mediastinum": {"label": "mediastinum", "rid": "RID1310"},
    "lymph node": {"label": "lymph node", "rid": "RID13176"},
    # ... more concepts
}
```

### Context-Aware Resolution

```python
# Resolve with anatomical context
concept = resolver.resolve("middle lobe", context=["lung", "lobe"])
# Returns: "right middle lobe of lung" with RID13171
```

## Clinical Standards

### RECIST 1.1 Compliance

- **Target lesions**: Primary tumors ≥10mm, lymph nodes ≥10mm
- **Non-target lesions**: Subcentimeter lymph nodes
- **Measurements**: Longest diameter for tumors, short axis for nodes
- **Response criteria**: CR, PR, SD, PD

### AJCC TNM Staging

- **T-stage**: Based on primary tumor size and invasion
- **N-stage**: Based on lymph node involvement
- **M-stage**: Based on distant metastases
- **Stage groups**: I, II, IIIA, IIIB, IV

### IASLC Nodal Stations

Standard mediastinal lymph node stations:

- **1R/1L**: Highest mediastinal
- **2R/2L**: Upper paratracheal
- **4R/4L**: Lower paratracheal
- **7**: Subcarinal
- **10R/10L**: Hilar

## Configuration

### Environment Variables

```bash
# Required for RadLex API access
export BIOPORTAL_API_KEY="your_api_key_here"
```

### Cache Management

```python
# Use persistent cache
generator = OntologyConfigGenerator(
    use_radlex=True,
    cache_file="radlex_cache.json"
)
```

### Offline Mode

```python
# Work without API access
generator = OntologyConfigGenerator(use_radlex=False)
```

## Benefits

### For AI Benchmarking

- **Ontology ground truth**: RadLex-anchored annotations
- **Graph structure**: Enables graph neural networks
- **Temporal tracking**: Persistent lesion UIDs
- **Standardized metrics**: RECIST and TNM compliance

### For Clinical Research

- **Interoperability**: FHIR ImagingStudy compatibility
- **Graph queries**: Complex anatomical relationships
- **Longitudinal tracking**: Lesion evolution over time
- **Quality assurance**: Controlled vocabularies

### For Radiologists

- **Standardized terminology**: RadLex compliance
- **Anatomical precision**: Hierarchical relationships
- **Clinical context**: TNM staging integration
- **Temporal correlation**: Lesion tracking across studies

## Future Enhancements

### Planned Features

1. **FHIR Integration**: Direct FHIR ImagingStudy generation
2. **Graph Database**: Neo4j/GraphQL integration
3. **Visualization**: Interactive graph visualization
4. **Validation**: Automated ontology validation
5. **Expansion**: Support for other cancer types

### API Improvements

1. **Batch Resolution**: Bulk concept resolution
2. **Caching**: Distributed caching system
3. **Rate Limiting**: Intelligent rate limiting
4. **Fallback**: Multiple ontology sources

## References

- [RadLex](https://www.rsna.org/practice-tools/data-tools-and-standards/radlex-radiology-lexicon)
- [AJCC TNM Staging](https://cancerstaging.org/)
- [RECIST 1.1](https://www.eortc.org/app/uploads/2021/12/RECIST-Guidelines-version-1.1.pdf)
- [IASLC Nodal Map](https://www.iaslc.org/iaslc-nodal-map)
- [FHIR ImagingStudy](https://hl7.org/fhir/imagingstudy.html)

## Contributing

To contribute to the ontology integration:

1. **Validate RIDs**: Ensure seeded RIDs are correct
2. **Add concepts**: Expand seeded concept dictionary
3. **Improve resolution**: Enhance context-aware resolution
4. **Add tests**: Comprehensive test coverage
5. **Documentation**: Update this guide

## Support

For questions or issues:

1. Check the demonstration scripts
2. Review the generated sample configurations
3. Validate RadLex API access
4. Check cache and offline mode settings


