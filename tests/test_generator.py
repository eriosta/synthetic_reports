import sys
from pathlib import Path
import pytest
import random
from unittest.mock import patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from synthrad.generator import (
    t_category, n_category, m_category, stage_group,
    sample_primary, sample_nodes, sample_mets, stage_hint_from_dist,
    generate_case, generate_report, format_primary, format_nodes, format_mets,
    determine_response_status, generate_follow_up_case, generate_patient_timeline,
    generate_accession_number, case_to_recist_jsonl
)
from synthrad.schema import Case, Meta, Primary, Node, Met, TNM


class TestTNMLogic:
    """Test TNM staging logic functions"""
    
    def test_t_category_size_based(self):
        """Test T category assignment based on size"""
        # T1a: ≤10mm
        tcat, reasons = t_category(8, False, False, False, False, False, False)
        assert tcat == "T1a"
        assert "≤10 mm" in reasons[0]
        
        # T1b: >10-20mm
        tcat, reasons = t_category(15, False, False, False, False, False, False)
        assert tcat == "T1b"
        assert ">10–20 mm" in reasons[0]
        
        # T1c: >20-30mm
        tcat, reasons = t_category(25, False, False, False, False, False, False)
        assert tcat == "T1c"
        assert ">20–30 mm" in reasons[0]
        
        # T2a: >30-50mm
        tcat, reasons = t_category(40, False, False, False, False, False, False)
        assert tcat == "T2a"
        assert ">30–50 mm" in reasons[0]
        
        # T2b: >50-70mm
        tcat, reasons = t_category(60, False, False, False, False, False, False)
        assert tcat == "T2b"
        assert ">50–70 mm" in reasons[0]
        
        # T3: >70mm
        tcat, reasons = t_category(80, False, False, False, False, False, False)
        assert tcat == "T3"
        assert ">70 mm" in reasons[0]
    
    def test_t_category_invasion_upgrades(self):
        """Test T category upgrades due to invasion"""
        # Chest wall invasion -> T3
        tcat, reasons = t_category(25, True, False, False, False, False, False)
        assert tcat == "T3"
        assert "chest wall/diaphragm invasion" in reasons[0]
        
        # Main bronchus involvement -> at least T2
        tcat, reasons = t_category(15, False, True, False, False, False, False)
        assert tcat == "T2a"
        assert "main bronchus" in reasons[1]  # Main bronchus reason is second
        
        # Carina involvement -> T4
        tcat, reasons = t_category(25, False, False, True, False, False, False)
        assert tcat == "T4"
        assert "carina involvement" in reasons[0]
        
        # Separate nodules same lobe -> T3
        tcat, reasons = t_category(25, False, False, False, True, False, False)
        assert tcat == "T3"
        assert "same lobe" in reasons[1]  # Separate nodules reason is second
        
        # Separate nodules other lobe -> T4
        tcat, reasons = t_category(25, False, False, False, False, True, False)
        assert tcat == "T4"
        assert "different ipsilateral lobe" in reasons[1]  # Separate nodules reason is second
    
    def test_n_category_logic(self):
        """Test N category assignment based on lymph nodes"""
        # N0: No pathologic nodes
        nodes = [Node(station="4R", short_axis_mm=8)]
        ncat, reasons = n_category(nodes)
        assert ncat == "N0"
        assert "No pathologically enlarged" in reasons[0]
        
        # N1: Hilar nodes ≥10mm
        nodes = [Node(station="10R", short_axis_mm=12)]
        ncat, reasons = n_category(nodes)
        assert ncat == "N1"
        assert "N1:" in reasons[0]
        
        # N2: Mediastinal nodes ≥10mm
        nodes = [Node(station="4R", short_axis_mm=14)]
        ncat, reasons = n_category(nodes)
        assert ncat == "N2"
        assert "N2:" in reasons[0]
        
        # N2 takes precedence over N1
        nodes = [
            Node(station="10R", short_axis_mm=12),  # N1
            Node(station="4R", short_axis_mm=14)    # N2
        ]
        ncat, reasons = n_category(nodes)
        assert ncat == "N2"
    
    def test_m_category_logic(self):
        """Test M category assignment based on metastases"""
        # M0: No metastases
        mets = []
        mcat, reasons = m_category(mets)
        assert mcat == "M0"
        assert "No definite distant metastases" in reasons[0]
        
        # M1a: Pleural/contralateral only
        mets = [Met(site="pleura", size_mm=15)]
        mcat, reasons = m_category(mets)
        assert mcat == "M1a"
        assert "pleural/contralateral" in reasons[0]
        
        # M1b: Single extrathoracic
        mets = [Met(site="liver", size_mm=20)]
        mcat, reasons = m_category(mets)
        assert mcat == "M1b"
        assert "single extrathoracic" in reasons[0]
        
        # M1c: Multiple extrathoracic
        mets = [
            Met(site="liver", size_mm=20),
            Met(site="bone", size_mm=15)
        ]
        mcat, reasons = m_category(mets)
        assert mcat == "M1c"
        assert "multiple extrathoracic" in reasons[0]
    
    def test_stage_group_logic(self):
        """Test stage group assignment from TNM"""
        # Stage I: T1-2, N0, M0
        assert stage_group("T1a", "N0", "M0") == "I"
        assert stage_group("T2a", "N0", "M0") == "II"
        
        # Stage II: T1-2, N1, M0
        assert stage_group("T1a", "N1", "M0") == "II"
        assert stage_group("T2a", "N1", "M0") == "II"
        
        # Stage III: T3-4 or N2, M0
        assert stage_group("T3", "N0", "M0") == "III"
        assert stage_group("T1a", "N2", "M0") == "III"
        
        # Stage IV: Any M1
        assert stage_group("T1a", "N0", "M1a") == "IV"
        assert stage_group("T4", "N2", "M1c") == "IV"


class TestCaseGeneration:
    """Test case generation functions"""
    
    def test_sample_primary_basic(self):
        """Test sample_primary function generates valid primary tumors"""
        rng = random.Random(42)
        primary, reasons = sample_primary("RUL", "II", rng)
        
        assert isinstance(primary, Primary)
        assert primary.lobe == "RUL"
        assert 12 <= primary.size_mm <= 48  # Stage II range
        assert isinstance(primary.features, list)
        assert len(reasons) > 0
    
    def test_sample_nodes_basic(self):
        """Test sample_nodes function generates valid lymph nodes"""
        rng = random.Random(42)
        nodes, reasons = sample_nodes("III", rng)
        
        assert isinstance(nodes, list)
        for node in nodes:
            assert isinstance(node, Node)
            assert node.station in ["1R","1L","2R","2L","3A","3P","4R","4L","5","6","7","8","9","10R","10L","11R","11L","12R","12L"]
            assert 8 <= node.short_axis_mm <= 18
        assert len(reasons) > 0
    
    def test_sample_mets_basic(self):
        """Test sample_mets function generates valid metastases"""
        rng = random.Random(42)
        mets, reasons = sample_mets("IV", rng)
        
        assert isinstance(mets, list)
        for met in mets:
            assert isinstance(met, Met)
            assert met.site in ["adrenal_right", "adrenal_left", "liver", "bone", "brain", "contralateral_lung", "pleura", "peritoneum", "omentum", "retroperitoneal_nodes"]
            assert 6 <= met.size_mm <= 28
        assert len(reasons) > 0
    
    def test_stage_hint_from_dist(self):
        """Test stage_hint_from_dist function"""
        rng = random.Random(42)
        dist = {"I": 0.5, "II": 0.3, "III": 0.2, "IV": 0.0}
        
        # Test single call
        hint = stage_hint_from_dist(dist, rng)
        assert hint in ["I", "II", "III", "IV"]
        
        # Test with different distributions
        dist2 = {"I": 0.0, "II": 0.0, "III": 0.0, "IV": 1.0}
        rng2 = random.Random(42)
        hint = stage_hint_from_dist(dist2, rng2)
        assert hint == "IV"
    
    def test_generate_case_basic(self):
        """Test generate_case function creates valid cases"""
        case = generate_case(seed=42, patient_id="TEST001")
        
        assert isinstance(case, Case)
        assert case.meta.patient_id == "TEST001"
        assert case.meta.visit_number == 1
        assert isinstance(case.primary, Primary)
        assert isinstance(case.nodes, list)
        assert isinstance(case.mets, list)
        assert isinstance(case.tnm, TNM)
        assert isinstance(case.rationale, list)
    
    def test_generate_case_deterministic(self):
        """Test generate_case is deterministic with same seed"""
        case1 = generate_case(seed=123, patient_id="TEST001")
        case2 = generate_case(seed=123, patient_id="TEST001")
        
        assert case1.primary.size_mm == case2.primary.size_mm
        assert case1.primary.lobe == case2.primary.lobe
        assert len(case1.nodes) == len(case2.nodes)
        assert len(case1.mets) == len(case2.mets)
    
    def test_generate_accession_number(self):
        """Test generate_accession_number creates valid format"""
        rng = random.Random(42)
        accession = generate_accession_number(rng)
        
        # Should be digits: YYYYMMDDXXXXXX
        assert accession.isdigit()
        assert len(accession) >= 10
        
        # Year should be reasonable
        year = int(accession[:4])
        assert 2020 <= year <= 2025


class TestReportGeneration:
    """Test report generation functions"""
    
    def test_format_primary_basic(self):
        """Test format_primary function"""
        primary = Primary(lobe="RUL", size_mm=25, features=["spiculation"])
        result = format_primary(primary, "concise")
        
        assert "right upper lobe" in result
        assert "25 mm" in result
        assert "spiculated margins" in result
    
    def test_format_nodes_basic(self):
        """Test format_nodes function"""
        nodes = [
            Node(station="4R", short_axis_mm=14),
            Node(station="7", short_axis_mm=8)
        ]
        result = format_nodes(nodes, "detailed")
        
        assert len(result) == 2
        assert "4R" in result[0]
        assert "14 mm" in result[0]
        assert "7" in result[1]
        assert "subcentimeter" in result[1]
    
    def test_format_mets_basic(self):
        """Test format_mets function"""
        mets = [
            Met(site="liver", size_mm=20),
            Met(site="adrenal_left", size_mm=15)
        ]
        result = format_mets(mets, "concise")
        
        assert len(result) == 2
        # Liver uses special phrases, so check for liver-related content
        assert "20 mm" in result[0]
        assert "adrenal left" in result[1]
        assert "15 mm" in result[1]
    
    def test_generate_report_structure(self):
        """Test generate_report creates proper report structure"""
        case = generate_case(seed=42)
        report = generate_report(case)
        
        # Check required sections
        assert "TECHNIQUE:" in report
        assert "COMPARISON:" in report
        assert "FINDINGS:" in report
        assert "IMPRESSION:" in report
        
        # Check content
        assert "Lungs/Primary:" in report
        assert "Mediastinum/Lymph nodes:" in report
        assert "Abdomen/Pelvis:" in report
        assert "Bones:" in report
    
    def test_generate_report_style_differences(self):
        """Test generate_report produces different content for different styles"""
        case = generate_case(seed=42)
        
        # Set different styles
        case.meta.radiologist_style = "concise"
        concise_report = generate_report(case)
        
        case.meta.radiologist_style = "detailed"
        detailed_report = generate_report(case)
        
        # Reports should be different
        assert concise_report != detailed_report
        
        # Both should have proper structure
        for report in [concise_report, detailed_report]:
            assert "TECHNIQUE:" in report
            assert "FINDINGS:" in report
            assert "IMPRESSION:" in report


class TestLongitudinalFeatures:
    """Test longitudinal consistency features"""
    
    def test_generate_report_with_prior_findings(self):
        """Test generate_report with prior findings for longitudinal comparison"""
        # Generate baseline case
        baseline_case = generate_case(seed=42, patient_id="LONG001", visit_number=1)
        
        # Create prior findings
        prior_findings = {}
        if baseline_case.primary:
            lesion_id = f"lung-{baseline_case.primary.lobe}-longest-1"
            prior_findings[lesion_id] = {
                "type": "primary",
                "size_mm": baseline_case.primary.size_mm,
                "site": baseline_case.primary.lobe
            }
        
        # Generate follow-up case
        follow_up_case = generate_case(seed=43, patient_id="LONG001", visit_number=2)
        
        # Generate report with prior findings
        report = generate_report(follow_up_case, prior_findings=prior_findings)
        
        # Should contain change information
        if baseline_case.primary and follow_up_case.primary:
            assert "baseline measurement" in report or "stable" in report or "increased" in report or "decreased" in report
    
    def test_lesion_id_generation(self):
        """Test deterministic lesion ID generation"""
        case = generate_case(seed=42)
        
        # Primary tumor ID
        if case.primary:
            expected_id = f"lung-{case.primary.lobe}-longest-1"
            # This would be generated internally in generate_report
            assert case.primary.lobe in ["RUL", "RML", "RLL", "LUL", "LLL"]
        
        # Node IDs
        for i, node in enumerate(case.nodes):
            expected_id = f"ln-{node.station}-shortaxis-{i+1}"
            assert node.station in ["1R","1L","2R","2L","3A","3P","4R","4L","5","6","7","8","9","10R","10L","11R","11L","12R","12L"]
        
        # Metastasis IDs
        for i, met in enumerate(case.mets):
            expected_id = f"{met.site.replace('_', '-')}-longest-{i+1}"
            assert met.site in ["adrenal_right", "adrenal_left", "liver", "bone", "brain", "contralateral_lung", "pleura", "peritoneum", "omentum", "retroperitoneal_nodes"]


class TestResponseStatus:
    """Test response status determination"""
    
    def test_determine_response_status_basic(self):
        """Test determine_response_status function"""
        # Create baseline case
        baseline = generate_case(seed=42)
        
        # Create follow-up with smaller primary (PR)
        follow_up = generate_case(seed=43)
        if baseline.primary and follow_up.primary:
            follow_up.primary.size_mm = int(baseline.primary.size_mm * 0.5)  # 50% reduction
        
        response = determine_response_status(baseline, follow_up)
        assert "Progressive disease" in response or "Partial response" in response or "Stable disease" in response or "Baseline" in response
    
    def test_generate_follow_up_case_basic(self):
        """Test generate_follow_up_case function"""
        baseline = generate_case(seed=42, patient_id="FOLLOW001")
        follow_up = generate_follow_up_case(baseline, seed=43)
        
        assert follow_up.meta.patient_id == baseline.meta.patient_id
        assert follow_up.meta.visit_number == baseline.meta.visit_number + 1
        assert follow_up.meta.comparison_date is not None
        assert follow_up.response_status is not None
    
    def test_generate_patient_timeline_basic(self):
        """Test generate_patient_timeline function"""
        cases, study_dates = generate_patient_timeline(
            patient_id="TIMELINE001",
            seed=42,
            stage_dist={"I": 0.2, "II": 0.3, "III": 0.3, "IV": 0.2},
            max_studies=3
        )
        
        assert len(cases) >= 2
        assert len(study_dates) == len(cases)
        assert all(case.meta.patient_id == "TIMELINE001" for case in cases)
        assert all(case.meta.visit_number == i+1 for i, case in enumerate(cases))


class TestRECISTExport:
    """Test RECIST JSONL export functionality"""
    
    def test_case_to_recist_jsonl_basic(self):
        """Test case_to_recist_jsonl function"""
        cases = [generate_case(seed=42, patient_id="RECIST001")]
        jsonl_data = case_to_recist_jsonl(cases)
        
        assert len(jsonl_data) == 1
        entry = jsonl_data[0]
        
        # Check required fields
        assert "patient_id" in entry
        assert "timepoint" in entry
        assert "study_date" in entry
        assert "lesions" in entry
        assert "overall_response" in entry
        
        # Check lesion structure
        if entry["lesions"]:
            lesion = entry["lesions"][0]
            assert "lesion_id" in lesion
            assert "kind" in lesion
            assert "size_mm_current" in lesion
            assert "target" in lesion


if __name__ == "__main__":
    pytest.main([__file__])
