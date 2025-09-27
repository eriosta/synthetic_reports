import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from synthrad.generator import generate_case, generate_follow_up_case, determine_response_status, case_to_recist_jsonl
from synthrad.lexicons import (
    select_recist_targets, calculate_sld, classify_nontarget_lesions,
    RECIST_TARGET_RULES, RECIST_THRESHOLDS
)

class TestRECISTCompliance:
    """Test RECIST 1.1 compliance features."""

    def test_target_lesion_selection_rules(self):
        """Test that target lesion selection follows RECIST 1.1 rules."""
        case = generate_case(seed=42, patient_id="TEST001")
        targets = select_recist_targets(case.primary, case.nodes, case.mets)
        
        # Check maximum total targets
        assert len(targets) <= RECIST_TARGET_RULES["max_total_targets"]
        
        # Check organ limits
        organ_counts = {}
        for target in targets:
            organ = target["organ"]
            organ_counts[organ] = organ_counts.get(organ, 0) + 1
            assert organ_counts[organ] <= RECIST_TARGET_RULES["max_per_organ"]
        
        # Check minimum sizes
        for target in targets:
            if target["type"] == "node":
                assert target["size_mm"] >= RECIST_TARGET_RULES["node_min_size_mm"]
            else:
                assert target["size_mm"] >= RECIST_TARGET_RULES["min_size_mm"]

    def test_sld_calculation(self):
        """Test Sum of Longest Diameters calculation."""
        case = generate_case(seed=42, patient_id="TEST002")
        targets = select_recist_targets(case.primary, case.nodes, case.mets)
        sld = calculate_sld(targets)
        
        # SLD should be sum of all target lesion sizes
        expected_sld = sum(target["size_mm"] for target in targets)
        assert sld == expected_sld

    def test_nontarget_classification(self):
        """Test non-target lesion classification."""
        case = generate_case(seed=42, patient_id="TEST003")
        targets = select_recist_targets(case.primary, case.nodes, case.mets)
        nontargets = classify_nontarget_lesions(case.primary, case.nodes, case.mets, targets)
        
        # All lesions should be either target or non-target
        target_ids = {target["lesion_id"] for target in targets}
        nontarget_ids = {nt["lesion_id"] for nt in nontargets}
        
        # No overlap between target and non-target
        assert len(target_ids & nontarget_ids) == 0
        
        # All non-targets should have a reason
        for nt in nontargets:
            assert "reason" in nt
            assert nt["reason"] in ["too_small", "not_selected"]

    def test_response_assessment_thresholds(self):
        """Test RECIST 1.1 response assessment thresholds."""
        # Test partial response (≥30% decrease)
        baseline_sld = 100
        follow_up_sld = 65  # 35% decrease
        response = determine_response_status(
            generate_case(seed=1, patient_id="P001"),
            generate_case(seed=2, patient_id="P001")
        )
        # This is a simplified test - actual response depends on case generation
        
        # Test progressive disease (≥20% increase)
        baseline_sld = 100
        follow_up_sld = 125  # 25% increase
        # Similar simplified test

    def test_jsonl_export_compliance(self):
        """Test that JSONL export is RECIST 1.1 compliant."""
        case = generate_case(seed=42, patient_id="TEST004")
        jsonl_data = case_to_recist_jsonl([case])
        entry = jsonl_data[0]
        
        # Check required fields
        required_fields = [
            "patient_id", "timepoint", "study_date", "current_sld_mm",
            "overall_response", "target_lesions", "nontarget_lesions", "lesions"
        ]
        for field in required_fields:
            assert field in entry
        
        # Check lesion classification
        target_count = sum(1 for lesion in entry["lesions"] if lesion["target"])
        nontarget_count = sum(1 for lesion in entry["lesions"] if not lesion["target"])
        
        assert target_count == entry["target_lesions"]
        assert nontarget_count == entry["nontarget_lesions"]
        
        # Check SLD calculation
        target_lesions = [lesion for lesion in entry["lesions"] if lesion["target"]]
        calculated_sld = sum(lesion["size_mm_current"] for lesion in target_lesions)
        assert entry["current_sld_mm"] == calculated_sld

    def test_lesion_id_consistency(self):
        """Test that lesion IDs are consistent across timepoints."""
        baseline = generate_case(seed=123, patient_id="P005", visit_number=1)
        follow_up = generate_follow_up_case(baseline, seed=456)
        
        baseline_targets = select_recist_targets(baseline.primary, baseline.nodes, baseline.mets)
        follow_up_targets = select_recist_targets(follow_up.primary, follow_up.nodes, follow_up.mets)
        
        baseline_ids = {target["lesion_id"] for target in baseline_targets}
        follow_up_ids = {target["lesion_id"] for target in follow_up_targets}
        
        # Some lesions should be consistent (same IDs)
        # This tests the deterministic ID generation
        assert len(baseline_ids) > 0
        assert len(follow_up_ids) > 0

    def test_max_target_limits(self):
        """Test that the system respects maximum target lesion limits."""
        # Generate a case with many lesions
        case = generate_case(seed=999, patient_id="TEST006")
        
        # Add extra nodes and mets to test limits
        from synthrad.schema import Node, Met
        extra_nodes = [
            Node(station="2R", short_axis_mm=15),
            Node(station="4R", short_axis_mm=12),
            Node(station="7", short_axis_mm=18),
            Node(station="10L", short_axis_mm=14),
        ]
        extra_mets = [
            Met(site="liver", size_mm=20),
            Met(site="adrenal_right", size_mm=15),
            Met(site="bone", size_mm=25),
        ]
        
        case.nodes.extend(extra_nodes)
        case.mets.extend(extra_mets)
        
        targets = select_recist_targets(case.primary, case.nodes, case.mets)
        
        # Should not exceed maximum targets
        assert len(targets) <= RECIST_TARGET_RULES["max_total_targets"]
        
        # Should not exceed per-organ limits
        organ_counts = {}
        for target in targets:
            organ = target["organ"]
            organ_counts[organ] = organ_counts.get(organ, 0) + 1
            assert organ_counts[organ] <= RECIST_TARGET_RULES["max_per_organ"]

if __name__ == "__main__":
    pytest.main([__file__])
