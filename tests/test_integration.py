import sys
from pathlib import Path
import pytest
import random
import json
import tempfile
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from synthrad.generator import (
    generate_case, generate_report, generate_patient_timeline,
    write_case, case_to_recist_jsonl
)
from synthrad.schema import Case, Meta, Primary, Node, Met, TNM


class TestIntegration:
    """Integration tests for end-to-end functionality"""
    
    def test_full_case_generation_and_report(self):
        """Test complete case generation and report creation"""
        # Generate a case
        case = generate_case(seed=42, patient_id="INTEGRATION001")
        
        # Verify case structure
        assert isinstance(case, Case)
        assert case.meta.patient_id == "INTEGRATION001"
        assert case.meta.visit_number == 1
        assert case.meta.accession_number is not None
        assert case.meta.radiologist_style is not None
        
        # Verify primary tumor
        assert isinstance(case.primary, Primary)
        assert case.primary.lobe in ["RUL", "RML", "RLL", "LUL", "LLL"]
        assert case.primary.size_mm > 0
        assert isinstance(case.primary.features, list)
        
        # Verify nodes
        assert isinstance(case.nodes, list)
        for node in case.nodes:
            assert isinstance(node, Node)
            assert node.station in ["1R","1L","2R","2L","3A","3P","4R","4L","5","6","7","8","9","10R","10L","11R","11L","12R","12L"]
            assert node.short_axis_mm > 0
        
        # Verify mets
        assert isinstance(case.mets, list)
        for met in case.mets:
            assert isinstance(met, Met)
            assert met.site in ["adrenal_right", "adrenal_left", "liver", "bone", "brain", "contralateral_lung", "pleura", "peritoneum", "omentum", "retroperitoneal_nodes"]
            assert met.size_mm > 0
        
        # Verify TNM
        assert isinstance(case.tnm, TNM)
        assert case.tnm.T in ["T1a", "T1b", "T1c", "T2a", "T2b", "T3", "T4"]
        assert case.tnm.N in ["N0", "N1", "N2"]
        assert case.tnm.M in ["M0", "M1a", "M1b", "M1c"]
        assert case.tnm.stage_group in ["I", "II", "III", "IV"]
        
        # Generate report
        report = generate_report(case)
        
        # Verify report structure
        assert "TECHNIQUE:" in report
        assert "COMPARISON:" in report
        assert "FINDINGS:" in report
        assert "IMPRESSION:" in report
        
        # Verify report content
        assert "Lungs/Primary:" in report
        assert "Mediastinum/Lymph nodes:" in report
        assert "Pleura:" in report
        assert "Abdomen/Pelvis:" in report
        assert "Bones:" in report
        
        # Verify primary tumor is mentioned
        if case.primary:
            # Check for lobe name in report (may be abbreviated)
            lobe_mapping = {"RUL": "right upper", "RML": "right middle", "RLL": "right lower", 
                           "LUL": "left upper", "LLL": "left lower"}
            lobe_text = lobe_mapping.get(case.primary.lobe, case.primary.lobe.lower())
            assert lobe_text in report.lower()
            assert str(case.primary.size_mm) in report
        
        # Verify nodes are mentioned
        if case.nodes:
            for node in case.nodes:
                assert node.station in report
        
        # Verify mets are mentioned
        if case.mets:
            for met in case.mets:
                assert met.site.replace("_", " ") in report
    
    def test_patient_timeline_generation(self):
        """Test complete patient timeline generation"""
        # Generate patient timeline
        cases, study_dates = generate_patient_timeline(
            patient_id="TIMELINE001",
            seed=42,
            stage_dist={"I": 0.2, "II": 0.3, "III": 0.3, "IV": 0.2},
            max_studies=3
        )
        
        # Verify timeline structure
        assert len(cases) >= 2
        assert len(study_dates) == len(cases)
        
        # Verify case progression
        for i, case in enumerate(cases):
            assert case.meta.patient_id == "TIMELINE001"
            assert case.meta.visit_number == i + 1
            assert case.meta.comparison_date is not None or i == 0
        
        # Verify date progression
        for i in range(1, len(study_dates)):
            assert study_dates[i] > study_dates[i-1]
        
        # Generate reports for all cases
        reports = []
        for case in cases:
            report = generate_report(case)
            reports.append(report)
            
            # Verify each report is valid
            assert "TECHNIQUE:" in report
            assert "FINDINGS:" in report
            assert "IMPRESSION:" in report
        
        # Verify reports are different (due to different visit numbers)
        assert len(set(reports)) > 1
    
    def test_longitudinal_consistency_integration(self):
        """Test longitudinal consistency across multiple timepoints"""
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
        
        for i, node in enumerate(baseline_case.nodes):
            lesion_id = f"ln-{node.station}-shortaxis-{i+1}"
            prior_findings[lesion_id] = {
                "type": "node",
                "size_mm": node.short_axis_mm,
                "site": node.station
            }
        
        for i, met in enumerate(baseline_case.mets):
            lesion_id = f"{met.site.replace('_', '-')}-longest-{i+1}"
            prior_findings[lesion_id] = {
                "type": "metastasis",
                "size_mm": met.size_mm,
                "site": met.site
            }
        
        # Generate follow-up case
        follow_up_case = generate_case(seed=43, patient_id="LONG001", visit_number=2)
        
        # Manually modify for specific changes
        if baseline_case.primary:
            follow_up_case.primary = baseline_case.primary
            follow_up_case.primary.size_mm = baseline_case.primary.size_mm + 2  # Small change
        
        follow_up_case.nodes = baseline_case.nodes.copy()
        follow_up_case.mets = baseline_case.mets.copy()
        
        # Generate reports
        baseline_report = generate_report(baseline_case)
        follow_up_report = generate_report(follow_up_case, prior_findings=prior_findings)
        
        # Verify both reports are valid
        assert "TECHNIQUE:" in baseline_report
        assert "FINDINGS:" in baseline_report
        assert "IMPRESSION:" in baseline_report
        
        assert "TECHNIQUE:" in follow_up_report
        assert "FINDINGS:" in follow_up_report
        assert "IMPRESSION:" in follow_up_report
        
        # Verify follow-up report contains change information
        if baseline_case.primary:
            assert "baseline measurement" in follow_up_report or "stable" in follow_up_report or "increased" in follow_up_report or "decreased" in follow_up_report
    
    def test_file_output_integration(self):
        """Test file output functionality"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Generate a case
            case = generate_case(seed=42, patient_id="FILE001")
            
            # Write case to files
            write_case(case, temp_dir, "test_case")
            
            # Verify files were created
            patient_dir = os.path.join(temp_dir, case.meta.patient_id)
            study_dir = os.path.join(patient_dir, f"study_{case.meta.visit_number:02d}")
            
            assert os.path.exists(patient_dir)
            assert os.path.exists(study_dir)
            
            # Verify TXT file
            txt_file = os.path.join(study_dir, f"{case.meta.accession_number}.txt")
            assert os.path.exists(txt_file)
            
            with open(txt_file, 'r') as f:
                content = f.read()
                assert "TECHNIQUE:" in content
                assert "FINDINGS:" in content
                assert "IMPRESSION:" in content
            
            # Verify JSON file
            json_file = os.path.join(study_dir, f"{case.meta.accession_number}.json")
            assert os.path.exists(json_file)
            
            with open(json_file, 'r') as f:
                data = json.load(f)
                assert "meta" in data
                assert "clinical_data" in data
                assert "anatomic_mapping" in data
                
                # Verify meta data
                assert data["meta"]["patient_id"] == "FILE001"
                assert data["meta"]["visit_number"] == 1
                
                # Verify clinical data
                assert "primary" in data["clinical_data"]
                assert "nodes" in data["clinical_data"]
                assert "mets" in data["clinical_data"]
                assert "tnm" in data["clinical_data"]
    
    def test_recist_jsonl_export_integration(self):
        """Test RECIST JSONL export functionality"""
        # Generate multiple cases
        cases = []
        for i in range(3):
            case = generate_case(seed=42+i, patient_id=f"RECIST{i:03d}")
            cases.append(case)
        
        # Export to JSONL format
        jsonl_data = case_to_recist_jsonl(cases)
        
        # Verify JSONL structure
        assert len(jsonl_data) == 3
        
        for entry in jsonl_data:
            # Verify required fields
            assert "patient_id" in entry
            assert "timepoint" in entry
            assert "study_date" in entry
            assert "lesions" in entry
            assert "overall_response" in entry
            
            # Verify lesion structure
            if entry["lesions"]:
                lesion = entry["lesions"][0]
                assert "lesion_id" in lesion
                assert "kind" in lesion
                assert "size_mm_current" in lesion
                assert "target" in lesion
        
        # Test with study dates
        import datetime
        study_dates = [
            datetime.datetime.now() - datetime.timedelta(days=365),
            datetime.datetime.now() - datetime.timedelta(days=300),
            datetime.datetime.now() - datetime.timedelta(days=200)
        ]
        
        jsonl_data_with_dates = case_to_recist_jsonl(cases, study_dates)
        
        # Verify dates are included
        for i, entry in enumerate(jsonl_data_with_dates):
            assert entry["study_date"] == study_dates[i].strftime("%Y-%m-%d")
    
    def test_style_consistency_integration(self):
        """Test style consistency across different functions"""
        # Generate cases with different styles
        concise_case = generate_case(seed=42, patient_id="STYLE001")
        concise_case.meta.radiologist_style = "concise"
        
        detailed_case = generate_case(seed=42, patient_id="STYLE001")
        detailed_case.meta.radiologist_style = "detailed"
        
        # Generate reports
        concise_report = generate_report(concise_case)
        detailed_report = generate_report(detailed_case)
        
        # Verify both reports are valid
        assert "TECHNIQUE:" in concise_report
        assert "FINDINGS:" in concise_report
        assert "IMPRESSION:" in concise_report
        
        assert "TECHNIQUE:" in detailed_report
        assert "FINDINGS:" in detailed_report
        assert "IMPRESSION:" in detailed_report
        
        # Verify reports are different
        assert concise_report != detailed_report
        
        # Verify style-specific content (remove nodes to test normal mediastinum phrasing)
        concise_case.nodes = []
        detailed_case.nodes = []
        
        concise_report = generate_report(concise_case)
        detailed_report = generate_report(detailed_case)
        
        assert "No pathologic mediastinal adenopathy" in concise_report
        assert "Mediastinum demonstrates normal contours" in detailed_report or "No mediastinal mass" in detailed_report
    
    def test_modality_specific_integration(self):
        """Test modality-specific report generation"""
        case = generate_case(seed=42, patient_id="MODALITY001")
        
        # Test CT report
        ct_report = generate_report(case, modality="CT")
        assert "CT chest, abdomen, and pelvis" in ct_report
        assert "IV contrast" in ct_report
        
        # Test PET-CT report
        pet_report = generate_report(case, modality="PET-CT")
        assert "FDG PET-CT" in pet_report
        assert "SUVmean" in pet_report
        
        # Test PET report
        pet_report2 = generate_report(case, modality="PET")
        assert "FDG PET-CT" in pet_report2
        assert "SUVmean" in pet_report2
    
    def test_deterministic_behavior_integration(self):
        """Test deterministic behavior across multiple runs"""
        # Generate cases with same seed
        case1 = generate_case(seed=42, patient_id="DETERMINISTIC001")
        case2 = generate_case(seed=42, patient_id="DETERMINISTIC001")
        
        # Verify cases are identical
        assert case1.primary.size_mm == case2.primary.size_mm
        assert case1.primary.lobe == case2.primary.lobe
        assert len(case1.nodes) == len(case2.nodes)
        assert len(case1.mets) == len(case2.mets)
        assert case1.tnm.T == case2.tnm.T
        assert case1.tnm.N == case2.tnm.N
        assert case1.tnm.M == case2.tnm.M
        assert case1.tnm.stage_group == case2.tnm.stage_group
        
        # Generate reports
        report1 = generate_report(case1)
        report2 = generate_report(case2)
        
        # Verify reports are similar (may have minor differences due to random elements)
        assert "TECHNIQUE:" in report1
        assert "TECHNIQUE:" in report2
        assert "FINDINGS:" in report1
        assert "FINDINGS:" in report2
        
        # Test patient timeline determinism
        cases1, dates1 = generate_patient_timeline("DETERMINISTIC002", seed=42, stage_dist={"I": 0.25, "II": 0.25, "III": 0.25, "IV": 0.25}, max_studies=3)
        cases2, dates2 = generate_patient_timeline("DETERMINISTIC002", seed=42, stage_dist={"I": 0.25, "II": 0.25, "III": 0.25, "IV": 0.25}, max_studies=3)
        
        # Verify timelines are identical
        assert len(cases1) == len(cases2)
        assert len(dates1) == len(dates2)
        
        for i, (case1, case2) in enumerate(zip(cases1, cases2)):
            assert case1.primary.size_mm == case2.primary.size_mm
            assert case1.primary.lobe == case2.primary.lobe
            assert len(case1.nodes) == len(case2.nodes)
            assert len(case1.mets) == len(case2.mets)
    
    def test_error_handling_integration(self):
        """Test error handling in integration scenarios"""
        # Test with invalid case data
        case = generate_case(seed=42, patient_id="ERROR001")
        
        # Manually corrupt some data
        case.primary.size_mm = -5  # Invalid size
        if case.nodes:
            case.nodes[0].short_axis_mm = -10  # Invalid node size
        if case.mets:
            case.mets[0].size_mm = -15  # Invalid met size
        
        # Should still generate valid report
        report = generate_report(case)
        assert "TECHNIQUE:" in report
        assert "FINDINGS:" in report
        assert "IMPRESSION:" in report
        
        # Test with empty case
        empty_case = Case(
            meta=Meta(patient_id="EMPTY001", visit_number=1),
            primary=None,
            nodes=[],
            mets=[],
            tnm=TNM(T="T0", N="N0", M="M0", stage_group="I"),
            rationale=[]
        )
        
        report = generate_report(empty_case)
        assert "TECHNIQUE:" in report
        assert "FINDINGS:" in report
        assert "IMPRESSION:" in report
        assert "Clear lungs" in report


if __name__ == "__main__":
    pytest.main([__file__])
