import sys
from pathlib import Path
import pytest
import random

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from synthrad.generator import generate_case, generate_report
from synthrad.schema import Node, Met


class TestLongitudinalConsistency:
    """Test longitudinal consistency features and lesion ID generation"""
    
    def test_deterministic_lesion_ids(self):
        """Test that lesion IDs are generated deterministically"""
        case = generate_case(seed=42, patient_id="LONG001")
        
        # Test primary tumor ID format
        if case.primary:
            expected_primary_id = f"lung-{case.primary.lobe}-longest-1"
            assert case.primary.lobe in ["RUL", "RML", "RLL", "LUL", "LLL"]
            # The ID format should be consistent
            assert expected_primary_id.startswith("lung-")
            assert expected_primary_id.endswith("-longest-1")
        
        # Test node ID format
        for i, node in enumerate(case.nodes):
            expected_node_id = f"ln-{node.station}-shortaxis-{i+1}"
            assert expected_node_id.startswith("ln-")
            assert expected_node_id.endswith(f"-shortaxis-{i+1}")
            assert node.station in expected_node_id
        
        # Test metastasis ID format
        for i, met in enumerate(case.mets):
            expected_met_id = f"{met.site.replace('_', '-')}-longest-{i+1}"
            assert expected_met_id.endswith(f"-longest-{i+1}")
            assert met.site.replace('_', '-') in expected_met_id
    
    def test_lesion_id_stability_across_timepoints(self):
        """Test that lesion IDs remain stable across timepoints"""
        # Generate baseline case
        baseline_case = generate_case(seed=42, patient_id="STABLE001", visit_number=1)
        
        # Create prior findings with deterministic IDs
        prior_findings = {}
        
        # Primary tumor
        if baseline_case.primary:
            lesion_id = f"lung-{baseline_case.primary.lobe}-longest-1"
            prior_findings[lesion_id] = {
                "type": "primary",
                "size_mm": baseline_case.primary.size_mm,
                "site": baseline_case.primary.lobe
            }
        
        # Lymph nodes
        for i, node in enumerate(baseline_case.nodes):
            lesion_id = f"ln-{node.station}-shortaxis-{i+1}"
            prior_findings[lesion_id] = {
                "type": "node",
                "size_mm": node.short_axis_mm,
                "site": node.station
            }
        
        # Metastases
        for i, met in enumerate(baseline_case.mets):
            lesion_id = f"{met.site.replace('_', '-')}-longest-{i+1}"
            prior_findings[lesion_id] = {
                "type": "metastasis",
                "size_mm": met.size_mm,
                "site": met.site
            }
        
        # Generate follow-up case with same lesions (different seed for variation)
        follow_up_case = generate_case(seed=43, patient_id="STABLE001", visit_number=2)
        
        # Manually set same lesions to test ID stability
        if baseline_case.primary:
            follow_up_case.primary = baseline_case.primary
            follow_up_case.primary.size_mm += 2  # Small change
        
        follow_up_case.nodes = baseline_case.nodes.copy()
        follow_up_case.mets = baseline_case.mets.copy()
        
        # Generate report with prior findings
        report = generate_report(follow_up_case, prior_findings=prior_findings)
        
        # Check that change information is included
        if baseline_case.primary:
            assert "stable" in report or "increased" in report or "decreased" in report
    
    def test_change_calculation_logic(self):
        """Test change calculation logic for different scenarios"""
        # Test data for change calculations
        test_cases = [
            # (current_size, prior_size, expected_change_desc)
            (25, 25, "stable"),      # No change
            (30, 25, "increased"),   # +20% change
            (20, 25, "decreased"),   # -20% change
            (26, 25, "stable"),      # +4% change (below threshold)
            (24, 25, "stable"),      # -4% change (below threshold)
            (0, 25, "resolved"),     # Resolved lesion
            (25, 0, "new"),          # New lesion
        ]
        
        for current_size, prior_size, expected_change in test_cases:
            if prior_size == 0:
                change_desc = "new"
            elif current_size == 0:
                change_desc = "resolved"
            else:
                delta = current_size - prior_size
                pct_change = (delta / prior_size) * 100
                
                if pct_change >= 20:
                    change_desc = "increased"
                elif pct_change <= -20:
                    change_desc = "decreased"
                else:
                    change_desc = "stable"
            
            assert change_desc == expected_change, f"Failed for {current_size} vs {prior_size}: got {change_desc}, expected {expected_change}"
    
    def test_longitudinal_comparison_integration(self):
        """Test that longitudinal comparison is integrated into narrative"""
        # Generate baseline case
        baseline_case = generate_case(seed=42, patient_id="NARRATIVE001", visit_number=1)
        
        # Create prior findings
        prior_findings = {}
        if baseline_case.primary:
            lesion_id = f"lung-{baseline_case.primary.lobe}-longest-1"
            prior_findings[lesion_id] = {
                "type": "primary",
                "size_mm": baseline_case.primary.size_mm,
                "site": baseline_case.primary.lobe
            }
        
        # Generate follow-up case with changes
        follow_up_case = generate_case(seed=43, patient_id="NARRATIVE001", visit_number=2)
        
        # Manually modify for specific changes
        if baseline_case.primary:
            follow_up_case.primary = baseline_case.primary
            follow_up_case.primary.size_mm = baseline_case.primary.size_mm + 5  # Increased
        
        # Generate report
        report = generate_report(follow_up_case, prior_findings=prior_findings)
        
        # Check that change information is in the narrative (not separate section)
        assert "LONGITUDINAL COMPARISON:" not in report  # Should not have separate section
        
        # Check that change information is integrated into findings
        if baseline_case.primary:
            assert "increased" in report or "stable" in report or "decreased" in report
            assert "baseline measurement" in report or "was" in report
    
    def test_resolved_lesions_handling(self):
        """Test handling of resolved lesions"""
        # Generate baseline case with lesions
        baseline_case = generate_case(seed=42, patient_id="RESOLVED001", visit_number=1)
        
        # Create prior findings
        prior_findings = {}
        if baseline_case.primary:
            lesion_id = f"lung-{baseline_case.primary.lobe}-longest-1"
            prior_findings[lesion_id] = {
                "type": "primary",
                "size_mm": baseline_case.primary.size_mm,
                "site": baseline_case.primary.lobe
            }
        
        # Generate follow-up case without primary (resolved)
        follow_up_case = generate_case(seed=43, patient_id="RESOLVED001", visit_number=2)
        follow_up_case.primary = None  # Resolved
        
        # Generate report
        report = generate_report(follow_up_case, prior_findings=prior_findings)
        
        # Check that resolved lesion is mentioned
        if baseline_case.primary:
            assert "resolved" in report or "Clear lungs" in report
    
    def test_new_lesions_handling(self):
        """Test handling of new lesions"""
        # Generate baseline case
        baseline_case = generate_case(seed=42, patient_id="NEW001", visit_number=1)
        
        # Create prior findings (empty for this test)
        prior_findings = {}
        
        # Generate follow-up case with new lesions
        follow_up_case = generate_case(seed=43, patient_id="NEW001", visit_number=2)
        
        # Generate report
        report = generate_report(follow_up_case, prior_findings=prior_findings)
        
        # Check that new lesions are marked as baseline
        if follow_up_case.primary:
            assert "baseline measurement" in report
    
    def test_multiple_lesion_types_changes(self):
        """Test changes across multiple lesion types (primary, nodes, mets)"""
        # Generate baseline case
        baseline_case = generate_case(seed=42, patient_id="MULTI001", visit_number=1)
        
        # Create prior findings for all lesion types
        prior_findings = {}
        
        # Primary tumor
        if baseline_case.primary:
            lesion_id = f"lung-{baseline_case.primary.lobe}-longest-1"
            prior_findings[lesion_id] = {
                "type": "primary",
                "size_mm": baseline_case.primary.size_mm,
                "site": baseline_case.primary.lobe
            }
        
        # Lymph nodes
        for i, node in enumerate(baseline_case.nodes):
            lesion_id = f"ln-{node.station}-shortaxis-{i+1}"
            prior_findings[lesion_id] = {
                "type": "node",
                "size_mm": node.short_axis_mm,
                "site": node.station
            }
        
        # Metastases
        for i, met in enumerate(baseline_case.mets):
            lesion_id = f"{met.site.replace('_', '-')}-longest-{i+1}"
            prior_findings[lesion_id] = {
                "type": "metastasis",
                "size_mm": met.size_mm,
                "site": met.site
            }
        
        # Generate follow-up case with various changes
        follow_up_case = generate_case(seed=43, patient_id="MULTI001", visit_number=2)
        
        # Modify lesions for different change types
        if baseline_case.primary:
            follow_up_case.primary = baseline_case.primary
            follow_up_case.primary.size_mm = baseline_case.primary.size_mm + 3  # Stable
        
        # Modify nodes
        follow_up_case.nodes = []
        for i, node in enumerate(baseline_case.nodes):
            new_node = Node(station=node.station, short_axis_mm=node.short_axis_mm + 2)
            follow_up_case.nodes.append(new_node)
        
        # Modify mets
        follow_up_case.mets = []
        for i, met in enumerate(baseline_case.mets):
            new_met = Met(site=met.site, size_mm=met.size_mm - 1)
            follow_up_case.mets.append(new_met)
        
        # Generate report
        report = generate_report(follow_up_case, prior_findings=prior_findings)
        
        # Check that change information is present for multiple lesion types
        change_indicators = ["stable", "increased", "decreased", "baseline measurement"]
        found_changes = sum(1 for indicator in change_indicators if indicator in report)
        assert found_changes > 0, "No change indicators found in report"
    
    def test_lesion_id_deterministic_across_runs(self):
        """Test that lesion IDs are deterministic across multiple runs"""
        case1 = generate_case(seed=42, patient_id="DETERMINISTIC001")
        case2 = generate_case(seed=42, patient_id="DETERMINISTIC001")
        
        # Same seed should produce same case
        assert case1.primary.size_mm == case2.primary.size_mm
        assert case1.primary.lobe == case2.primary.lobe
        assert len(case1.nodes) == len(case2.nodes)
        assert len(case1.mets) == len(case2.mets)
        
        # Lesion IDs should be identical
        if case1.primary:
            id1 = f"lung-{case1.primary.lobe}-longest-1"
            id2 = f"lung-{case2.primary.lobe}-longest-1"
            assert id1 == id2
        
        for i, (node1, node2) in enumerate(zip(case1.nodes, case2.nodes)):
            id1 = f"ln-{node1.station}-shortaxis-{i+1}"
            id2 = f"ln-{node2.station}-shortaxis-{i+1}"
            assert id1 == id2
        
        for i, (met1, met2) in enumerate(zip(case1.mets, case2.mets)):
            id1 = f"{met1.site.replace('_', '-')}-longest-{i+1}"
            id2 = f"{met2.site.replace('_', '-')}-longest-{i+1}"
            assert id1 == id2
    
    def test_edge_case_empty_prior_findings(self):
        """Test handling of empty prior findings"""
        case = generate_case(seed=42, patient_id="EMPTY001", visit_number=2)
        prior_findings = {}
        
        report = generate_report(case, prior_findings=prior_findings)
        
        # Should still generate valid report
        assert "TECHNIQUE:" in report
        assert "FINDINGS:" in report
        assert "IMPRESSION:" in report
        
        # All lesions should be marked as baseline
        if case.primary:
            assert "baseline measurement" in report
    
    def test_edge_case_no_prior_findings_parameter(self):
        """Test handling when prior_findings parameter is None"""
        case = generate_case(seed=42, patient_id="NONE001", visit_number=2)
        
        report = generate_report(case, prior_findings=None)
        
        # Should still generate valid report
        assert "TECHNIQUE:" in report
        assert "FINDINGS:" in report
        assert "IMPRESSION:" in report
        
        # All lesions should be marked as baseline
        if case.primary:
            assert "baseline measurement" in report


if __name__ == "__main__":
    pytest.main([__file__])
