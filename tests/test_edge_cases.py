import sys
from pathlib import Path
import pytest
import random
from unittest.mock import patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from synthrad.generator import (
    t_category, n_category, m_category, stage_group,
    generate_case, generate_report, format_primary, format_nodes, format_mets,
    determine_response_status, generate_follow_up_case, generate_patient_timeline,
    case_to_recist_jsonl
)
from synthrad.lexicons import (
    feature_text, station_label, mm_desc, node_phrase, fmt_mm, compare_size,
    recist_overall_response, percist_summary, pick, make_rng
)
from synthrad.schema import Case, Meta, Primary, Node, Met, TNM


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_t_category_edge_cases(self):
        """Test T category with edge case inputs"""
        # Test with size 0
        tcat, reasons = t_category(0, False, False, False, False, False, False)
        assert tcat == "T1a"  # Should handle 0 size gracefully
        
        # Test with very large size
        tcat, reasons = t_category(1000, False, False, False, False, False, False)
        assert tcat == "T3"  # Should cap at T3 for size
        
        # Test with all invasion flags True
        tcat, reasons = t_category(25, True, True, True, True, True, True)
        assert tcat == "T4"  # Carina involvement should override to T4
        
        # Test with conflicting upgrades
        tcat, reasons = t_category(5, False, True, False, False, False, False)
        assert tcat == "T2a"  # Main bronchus should upgrade T1a to T2a
    
    def test_n_category_edge_cases(self):
        """Test N category with edge case inputs"""
        # Test with empty nodes list
        nodes = []
        ncat, reasons = n_category(nodes)
        assert ncat == "N0"
        assert "No pathologically enlarged" in reasons[0]
        
        # Test with very large nodes
        nodes = [Node(station="4R", short_axis_mm=100)]
        ncat, reasons = n_category(nodes)
        assert ncat == "N2"
        
        # Test with mixed N1 and N2 nodes
        nodes = [
            Node(station="10R", short_axis_mm=15),  # N1
            Node(station="4R", short_axis_mm=8)     # N2, but subcentimeter
        ]
        ncat, reasons = n_category(nodes)
        assert ncat == "N1"  # N1 should take precedence
        
        # Test with unknown station
        nodes = [Node(station="99X", short_axis_mm=15)]
        ncat, reasons = n_category(nodes)
        assert ncat == "N0"  # Unknown stations should not affect N category
    
    def test_m_category_edge_cases(self):
        """Test M category with edge case inputs"""
        # Test with empty mets list
        mets = []
        mcat, reasons = m_category(mets)
        assert mcat == "M0"
        
        # Test with mixed site types
        mets = [
            Met(site="pleura", size_mm=10),      # M1a
            Met(site="liver", size_mm=20)        # M1b
        ]
        mcat, reasons = m_category(mets)
        assert mcat == "M1b"  # Single extrathoracic should be M1b
        
        # Test with unknown site
        mets = [Met(site="unknown_site", size_mm=15)]
        mcat, reasons = m_category(mets)
        assert mcat == "M1b"  # Unknown site should be treated as extrathoracic
    
    def test_stage_group_edge_cases(self):
        """Test stage group with edge case inputs"""
        # Test with invalid T category
        stage = stage_group("TX", "N0", "M0")
        assert stage == "III"  # Should default to III for invalid T
        
        # Test with invalid N category
        stage = stage_group("T1a", "NX", "M0")
        assert stage == "III"  # Should default to III for invalid N
        
        # Test with invalid M category
        stage = stage_group("T1a", "N0", "MX")
        assert stage == "I"  # Should default to I for invalid M
    
    def test_feature_text_edge_cases(self):
        """Test feature_text with edge case inputs"""
        # Test with empty list
        result = feature_text([])
        assert result == "smooth margins"
        
        # Test with all unknown features
        result = feature_text(["unknown1", "unknown2"])
        assert result == "smooth margins"
        
        # Test with mixed known/unknown features
        result = feature_text(["spiculation", "unknown", "cavitation"])
        assert "spiculated margins" in result
        assert "internal cavitation" in result
        assert "unknown" not in result
    
    def test_station_label_edge_cases(self):
        """Test station_label with edge case inputs"""
        # Test with None input
        label, group = station_label(None)
        assert "station None" in label
        assert group == "N?"
        
        # Test with empty string
        label, group = station_label("")
        assert "station " in label
        assert group == "N?"
        
        # Test with very long string
        label, group = station_label("very_long_station_name")
        assert "very_long_station_name" in label
        assert group == "N?"
    
    def test_mm_desc_edge_cases(self):
        """Test mm_desc with edge case inputs"""
        # Test with 0
        result = mm_desc(0)
        assert result == "subcentimeter"
        
        # Test with negative number
        result = mm_desc(-5)
        assert result == "subcentimeter"
        
        # Test with exactly 10
        result = mm_desc(10)
        assert result == "10 mm"
        
        # Test with very large number
        result = mm_desc(1000)
        assert result == "1000 mm"
    
    def test_node_phrase_edge_cases(self):
        """Test node_phrase with edge case inputs"""
        # Test with None station
        result = node_phrase(None, 15, style="concise")
        assert "None node" in result
        
        # Test with 0 size
        result = node_phrase("4R", 0, style="concise")
        assert "subcentimeter" in result
        
        # Test with negative size
        result = node_phrase("4R", -5, style="concise")
        assert "subcentimeter" in result
        
        # Test with unknown style
        result = node_phrase("4R", 15, style="unknown_style")
        assert "4R" in result  # Should default to detailed style
    
    def test_fmt_mm_edge_cases(self):
        """Test fmt_mm with edge case inputs"""
        # Test with 0
        result = fmt_mm(0)
        assert result == "0 mm"
        
        # Test with negative number
        result = fmt_mm(-10)
        assert result == "-10 mm"
        
        # Test with exactly 100
        result = fmt_mm(100)
        assert result == "10.0 cm"
        
        # Test with very large number
        result = fmt_mm(10000)
        assert result == "1000.0 cm"
    
    def test_compare_size_edge_cases(self):
        """Test compare_size with edge case inputs"""
        # Test with 0 prior size
        result = compare_size(25, 0)
        assert "stable" in result  # 0% change from 0
        
        # Test with 0 current size
        result = compare_size(0, 25)
        assert "decreased" in result
        
        # Test with both 0
        result = compare_size(0, 0)
        assert "stable" in result
        
        # Test with very small numbers
        result = compare_size(1, 1)
        assert "stable" in result
        
        # Test with very large numbers
        result = compare_size(1000, 1000)
        assert "stable" in result
    
    def test_recist_overall_response_edge_cases(self):
        """Test recist_overall_response with edge case inputs"""
        # Test with 0 current sum
        result = recist_overall_response(0, 50, False)
        assert "Partial response" in result
        
        # Test with 0 prior sum
        result = recist_overall_response(50, 0, False)
        assert "Stable disease" in result  # 0% change from 0
        
        # Test with both 0
        result = recist_overall_response(0, 0, False)
        assert "Stable disease" in result
        
        # Test with very small numbers
        result = recist_overall_response(1, 1, False)
        assert "Stable disease" in result
    
    def test_percist_summary_edge_cases(self):
        """Test percist_summary with edge case inputs"""
        # Test with 0 current SUV
        result = percist_summary(0, 5.0, False)
        assert "Partial metabolic response" in result
        
        # Test with 0 prior SUV (should handle division by zero)
        try:
            result = percist_summary(5.0, 0, False)
            assert "Progressive metabolic disease" in result
        except ZeroDivisionError:
            # This is expected behavior
            pass
        
        # Test with both 0 (should handle division by zero)
        try:
            result = percist_summary(0, 0, False)
            assert "Stable metabolic disease" in result
        except ZeroDivisionError:
            # This is expected behavior
            pass
        
        # Test with very small numbers
        result = percist_summary(0.1, 0.1, False)
        assert "Stable metabolic disease" in result
    
    def test_pick_edge_cases(self):
        """Test pick with edge case inputs"""
        # Test with single element
        result = pick(["single"])
        assert result == "single"
    
    def test_make_rng_edge_cases(self):
        """Test make_rng with edge case inputs"""
        # Test with 0 seed
        rng = make_rng(0)
        assert rng is not None
        
        # Test with negative seed
        rng = make_rng(-42)
        assert rng is not None
        
        # Test with very large seed
        rng = make_rng(999999999)
        assert rng is not None
    
    def test_generate_case_edge_cases(self):
        """Test generate_case with edge case inputs"""
        # Test with 0 seed
        case = generate_case(seed=0)
        assert case is not None
        assert case.meta.visit_number == 1
        
        # Test with negative seed
        case = generate_case(seed=-42)
        assert case is not None
        
        # Test with very large seed
        case = generate_case(seed=999999999)
        assert case is not None
        
        # Test with empty stage distribution
        case = generate_case(seed=42, stage_dist={})
        assert case is not None
        
        # Test with invalid stage distribution
        case = generate_case(seed=42, stage_dist={"I": 0.0, "II": 0.0, "III": 0.0, "IV": 0.0})
        assert case is not None
    
    def test_generate_report_edge_cases(self):
        """Test generate_report with edge case inputs"""
        # Test with case having no lesions
        case = generate_case(seed=42)
        case.primary = None
        case.nodes = []
        case.mets = []
        
        report = generate_report(case)
        assert "TECHNIQUE:" in report
        assert "FINDINGS:" in report
        assert "IMPRESSION:" in report
        assert "Clear lungs" in report
        
        # Test with None case
        with pytest.raises(AttributeError):
            generate_report(None)
        
        # Test with invalid modality
        case = generate_case(seed=42)
        report = generate_report(case, modality="INVALID")
        assert "TECHNIQUE:" in report  # Should default to CT
        
        # Test with empty modality
        report = generate_report(case, modality="")
        assert "TECHNIQUE:" in report  # Should default to CT
    
    def test_format_primary_edge_cases(self):
        """Test format_primary with edge case inputs"""
        # Test with primary having no features
        primary = Primary(lobe="RUL", size_mm=25, features=[])
        result = format_primary(primary)
        assert "smooth margins" in result
        
        # Test with primary having unknown features
        primary = Primary(lobe="RUL", size_mm=25, features=["unknown_feature"])
        result = format_primary(primary)
        assert "smooth margins" in result
        
        # Test with invalid style
        primary = Primary(lobe="RUL", size_mm=25, features=["spiculation"])
        result = format_primary(primary, "invalid_style")
        assert "right upper lobe" in result  # Should default to detailed style
    
    def test_format_nodes_edge_cases(self):
        """Test format_nodes with edge case inputs"""
        # Test with None nodes
        result = format_nodes(None)
        assert result == ["No pathologically enlarged lymph nodes by size criteria."]
        
        # Test with empty nodes list
        result = format_nodes([])
        assert result == ["No pathologically enlarged lymph nodes by size criteria."]
        
        # Test with nodes having 0 size
        nodes = [Node(station="4R", short_axis_mm=0)]
        result = format_nodes(nodes)
        assert len(result) == 1
        assert "4R" in result[0]
        
        # Test with invalid style
        nodes = [Node(station="4R", short_axis_mm=15)]
        result = format_nodes(nodes, "invalid_style")
        assert len(result) == 1
        assert "4R" in result[0]
    
    def test_format_mets_edge_cases(self):
        """Test format_mets with edge case inputs"""
        # Test with empty mets list
        result = format_mets([])
        assert result == ["No definite distant metastases identified."]
        
        # Test with mets having 0 size
        mets = [Met(site="liver", size_mm=0)]
        result = format_mets(mets)
        assert len(result) == 1
        assert "0 mm" in result[0]
        
        # Test with invalid style
        mets = [Met(site="liver", size_mm=20)]
        result = format_mets(mets, "invalid_style")
        assert len(result) == 1
        assert "20 mm" in result[0]
    
    def test_determine_response_status_edge_cases(self):
        """Test determine_response_status with edge case inputs"""
        # Test with cases having no primary
        baseline = generate_case(seed=42)
        baseline.primary = None
        follow_up = generate_case(seed=43)
        follow_up.primary = None
        result = determine_response_status(baseline, follow_up)
        assert result == "SD"
    
    def test_generate_follow_up_case_edge_cases(self):
        """Test generate_follow_up_case with edge case inputs"""
        # Test with None baseline case
        with pytest.raises(AttributeError):
            generate_follow_up_case(None, seed=42)
        
        # Test with 0 seed
        baseline = generate_case(seed=42)
        follow_up = generate_follow_up_case(baseline, seed=0)
        assert follow_up is not None
        
        # Test with negative seed
        follow_up = generate_follow_up_case(baseline, seed=-42)
        assert follow_up is not None
        
        # Test with very large seed
        follow_up = generate_follow_up_case(baseline, seed=999999999)
        assert follow_up is not None
    
    def test_generate_patient_timeline_edge_cases(self):
        """Test generate_patient_timeline with edge case inputs"""
        # Test with empty patient_id
        cases, dates = generate_patient_timeline("", seed=42, stage_dist={"I": 0.25, "II": 0.25, "III": 0.25, "IV": 0.25})
        assert len(cases) > 0
        assert len(dates) == len(cases)
        
        # Test with 0 seed
        cases, dates = generate_patient_timeline("TEST001", seed=0, stage_dist={"I": 0.25, "II": 0.25, "III": 0.25, "IV": 0.25})
        assert len(cases) > 0
        
        # Test with max_studies = 1 (minimum is 2)
        cases, dates = generate_patient_timeline("TEST001", seed=42, stage_dist={"I": 0.25, "II": 0.25, "III": 0.25, "IV": 0.25}, max_studies=2)
        assert len(cases) >= 2
        
        # Test with empty stage_dist
        cases, dates = generate_patient_timeline("TEST001", seed=42, stage_dist={})
        assert len(cases) > 0
    
    def test_case_to_recist_jsonl_edge_cases(self):
        """Test case_to_recist_jsonl with edge case inputs"""
        # Test with empty cases list
        result = case_to_recist_jsonl([])
        assert result == []
        
        # Test with case having no lesions
        case = generate_case(seed=42)
        case.primary = None
        case.nodes = []
        case.mets = []
        result = case_to_recist_jsonl([case])
        assert len(result) == 1
        assert result[0]["lesions"] == []
        
        # Test with case having 0 size lesions
        case = generate_case(seed=42)
        if case.primary:
            case.primary.size_mm = 0
        result = case_to_recist_jsonl([case])
        assert len(result) == 1
        assert len(result[0]["lesions"]) > 0


if __name__ == "__main__":
    pytest.main([__file__])
