# SynthRad Test Suite

This directory contains comprehensive tests for the SynthRad synthetic radiology report generation system.

## Test Files

### Core Tests
- **`test_basic.py`** - Basic functionality test
- **`test_lexicons.py`** - Tests for lexicons.py data structures and functions
- **`test_generator.py`** - Tests for generator.py core functionality
- **`test_longitudinal.py`** - Tests for longitudinal consistency features
- **`test_styles.py`** - Tests for radiologist style differences
- **`test_edge_cases.py`** - Tests for edge cases and error conditions
- **`test_integration.py`** - End-to-end integration tests

### Test Runner
- **`run_tests.py`** - Test runner script

## Test Coverage

### Lexicons Tests (`test_lexicons.py`)
- **Data Structure Tests**: LOBES, SIDE_FROM_LOBE, NODE_STATIONS, STATION_METADATA, MET_SITES, RADIOLOGIST_STYLES, FEATURE_CANON
- **Function Tests**: feature_text, station_label, mm_desc, node_phrase, fmt_mm, compare_size, recist_overall_response, percist_summary, pick, make_rng

### Generator Tests (`test_generator.py`)
- **TNM Logic Tests**: t_category, n_category, m_category, stage_group
- **Case Generation Tests**: sample_primary, sample_nodes, sample_mets, stage_hint_from_dist, generate_case, generate_accession_number
- **Report Generation Tests**: format_primary, format_nodes, format_mets, generate_report
- **Longitudinal Features Tests**: generate_report with prior_findings, lesion_id_generation
- **Response Status Tests**: determine_response_status, generate_follow_up_case, generate_patient_timeline
- **RECIST Export Tests**: case_to_recist_jsonl

### Longitudinal Tests (`test_longitudinal.py`)
- **Deterministic Lesion IDs**: Test stable lesion ID generation across timepoints
- **Change Calculation Logic**: Test size change calculations and thresholds
- **Narrative Integration**: Test that longitudinal changes are integrated into report narrative
- **Resolved/New Lesions**: Test handling of resolved and new lesions
- **Multiple Lesion Types**: Test changes across primary, nodes, and metastases
- **Edge Cases**: Test empty prior findings, None parameters

### Style Tests (`test_styles.py`)
- **Style Dictionary Structure**: Test RADIOLOGIST_STYLES completeness
- **Style Differences**: Test that concise vs detailed styles produce different content
- **Primary Lesion Phrases**: Test style-specific primary tumor descriptions
- **Node Phrases**: Test style-specific lymph node descriptions
- **Metastasis Phrases**: Test style-specific metastasis descriptions
- **Style Aliases**: Test that aliases map to correct styles
- **Report Structure**: Test consistent report structure across styles
- **Feature Text**: Test canonical feature mapping and deduplication
- **Pathology Semantics**: Test pathologic vs non-pathologic node identification

### Edge Case Tests (`test_edge_cases.py`)
- **TNM Edge Cases**: Test with invalid inputs, extreme values, conflicting upgrades
- **Function Edge Cases**: Test with None, empty lists, negative values, very large numbers
- **Error Handling**: Test division by zero, index errors, type errors
- **Boundary Conditions**: Test exact thresholds, zero values, single elements

### Integration Tests (`test_integration.py`)
- **Full Case Generation**: Test complete case generation and report creation
- **Patient Timeline**: Test multi-timepoint patient timeline generation
- **Longitudinal Consistency**: Test longitudinal features across multiple timepoints
- **File Output**: Test file writing functionality
- **RECIST JSONL Export**: Test RECIST data export
- **Style Consistency**: Test style consistency across different functions
- **Modality Specific**: Test CT vs PET-CT report generation
- **Deterministic Behavior**: Test reproducibility with same seeds
- **Error Handling**: Test graceful handling of invalid data

## Running Tests

### Run All Tests
```bash
python tests/run_tests.py
```

### Run Specific Test File
```bash
python tests/run_tests.py lexicons
python tests/run_tests.py generator
python tests/run_tests.py longitudinal
python tests/run_tests.py styles
python tests/run_tests.py edge_cases
python tests/run_tests.py integration
```

### Run with pytest directly
```bash
pytest tests/ -v
pytest tests/test_lexicons.py -v
```

## Test Results

All 98 tests pass, covering:
- ✅ Data structure validation
- ✅ Function correctness
- ✅ TNM staging logic
- ✅ Report generation
- ✅ Style differences
- ✅ Longitudinal consistency
- ✅ Edge case handling
- ✅ Integration scenarios
- ✅ Error conditions

## Key Tested Assumptions

### TNM Staging
- T category based on size and invasion features
- N category based on lymph node stations and sizes
- M category based on metastatic sites
- Stage group assignment from TNM combination

### Report Generation
- Consistent report structure (TECHNIQUE, COMPARISON, FINDINGS, IMPRESSION)
- Style-specific phrasing differences
- Proper lesion descriptions with measurements
- Normal findings for each anatomic region

### Longitudinal Consistency
- Deterministic lesion ID generation
- Change calculation with 20% thresholds
- Narrative integration of changes
- Handling of resolved and new lesions

### Style Differences
- Concise vs detailed phrasing
- Pathologic vs non-pathologic node identification
- Canonical feature mapping
- Style alias mapping

### Error Handling
- Graceful handling of invalid inputs
- Division by zero protection
- Type error prevention
- Boundary condition handling
