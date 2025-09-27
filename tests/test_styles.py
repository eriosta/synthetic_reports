import sys
from pathlib import Path
import pytest
import random

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from synthrad.generator import generate_case, generate_report, format_primary, format_nodes, format_mets
from synthrad.lexicons import RADIOLOGIST_STYLES, node_phrase, feature_text
from synthrad.schema import Primary, Node, Met


class TestRadiologistStyles:
    """Test radiologist style differences and phrase generation"""
    
    def test_style_dictionary_structure(self):
        """Test that RADIOLOGIST_STYLES has correct structure"""
        assert "concise" in RADIOLOGIST_STYLES
        assert "detailed" in RADIOLOGIST_STYLES
        assert len(RADIOLOGIST_STYLES) == 2
        
        # Test that both styles have all required keys
        required_keys = [
            "normal_mediastinum", "normal_pleura", "normal_great_vessels",
            "normal_abdomen", "normal_bones", "artifact_phrases",
            "primary_lesion_phrases", "node_phrases", "metastasis_phrases"
        ]
        
        for style_name in RADIOLOGIST_STYLES:
            style_dict = RADIOLOGIST_STYLES[style_name]
            for key in required_keys:
                assert key in style_dict, f"Missing key {key} in style {style_name}"
                assert isinstance(style_dict[key], list), f"Key {key} should be a list in style {style_name}"
                assert len(style_dict[key]) > 0, f"Key {key} should have content in style {style_name}"
    
    def test_style_phrase_differences(self):
        """Test that different styles produce different phrases"""
        # Test normal mediastinum phrases
        concise_mediastinum = RADIOLOGIST_STYLES["concise"]["normal_mediastinum"]
        detailed_mediastinum = RADIOLOGIST_STYLES["detailed"]["normal_mediastinum"]
        
        assert concise_mediastinum != detailed_mediastinum
        assert len(concise_mediastinum[0]) < len(detailed_mediastinum[0])  # Concise should be shorter
        
        # Test normal pleura phrases
        concise_pleura = RADIOLOGIST_STYLES["concise"]["normal_pleura"]
        detailed_pleura = RADIOLOGIST_STYLES["detailed"]["normal_pleura"]
        
        assert concise_pleura != detailed_pleura
        
        # Test artifact phrases
        concise_artifacts = RADIOLOGIST_STYLES["concise"]["artifact_phrases"]
        detailed_artifacts = RADIOLOGIST_STYLES["detailed"]["artifact_phrases"]
        
        assert concise_artifacts != detailed_artifacts
        assert len(concise_artifacts[0]) < len(detailed_artifacts[0])  # Concise should be shorter
    
    def test_primary_lesion_phrase_differences(self):
        """Test that primary lesion phrases differ between styles"""
        concise_phrases = RADIOLOGIST_STYLES["concise"]["primary_lesion_phrases"]
        detailed_phrases = RADIOLOGIST_STYLES["detailed"]["primary_lesion_phrases"]
        
        assert concise_phrases != detailed_phrases
        
        # Test with actual primary tumor
        primary = Primary(lobe="RUL", size_mm=25, features=["spiculation"])
        
        concise_result = format_primary(primary, "concise")
        detailed_result = format_primary(primary, "detailed")
        
        assert concise_result != detailed_result
        assert "right upper lobe" in concise_result
        assert "right upper lobe" in detailed_result
        assert "25 mm" in concise_result
        assert "25 mm" in detailed_result
        assert "spiculated margins" in concise_result
        assert "spiculated margins" in detailed_result
    
    def test_node_phrase_style_differences(self):
        """Test that node phrases differ between styles"""
        # Test pathologic node
        concise_result = node_phrase("4R", 14, style="concise")
        detailed_result = node_phrase("4R", 14, style="detailed")
        
        assert concise_result != detailed_result
        assert "4R node" in concise_result
        assert "Enlarged" in detailed_result
        assert "paratracheal" in detailed_result
        assert "14 mm" in concise_result
        assert "14 mm" in detailed_result
        assert "pathologic" in concise_result
        
        # Test subcentimeter node
        concise_result = node_phrase("11L", 8, style="concise")
        detailed_result = node_phrase("11L", 8, style="detailed")
        
        assert concise_result != detailed_result
        assert "11L node" in concise_result
        assert "interlobar" in detailed_result
        assert "subcentimeter" in concise_result
        assert "subcentimeter" in detailed_result
        assert "pathologic" not in concise_result  # Subcentimeter nodes not pathologic
    
    def test_metastasis_phrase_differences(self):
        """Test that metastasis phrases differ between styles"""
        concise_phrases = RADIOLOGIST_STYLES["concise"]["metastasis_phrases"]
        detailed_phrases = RADIOLOGIST_STYLES["detailed"]["metastasis_phrases"]
        
        assert concise_phrases != detailed_phrases
        
        # Test with actual metastasis (non-liver to avoid special handling)
        mets = [Met(site="adrenal_left", size_mm=20)]
        
        concise_result = format_mets(mets, "concise")
        detailed_result = format_mets(mets, "detailed")
        
        assert concise_result != detailed_result
        assert "adrenal left" in concise_result[0]
        assert "adrenal left" in detailed_result[0]
        assert "20 mm" in concise_result[0]
        assert "20 mm" in detailed_result[0]
    
    def test_style_aliases(self):
        """Test that style aliases work correctly"""
        # Test that aliases map to correct styles
        case = generate_case(seed=42)
        
        # Test clinical -> concise
        case.meta.radiologist_style = "clinical"
        clinical_report = generate_report(case)
        
        case.meta.radiologist_style = "concise"
        concise_report = generate_report(case)
        
        # Should be similar (same style)
        assert "TECHNIQUE:" in clinical_report
        assert "TECHNIQUE:" in concise_report
        
        # Test academic -> detailed
        case.meta.radiologist_style = "academic"
        academic_report = generate_report(case)
        
        case.meta.radiologist_style = "detailed"
        detailed_report = generate_report(case)
        
        # Should be similar (same style)
        assert "TECHNIQUE:" in academic_report
        assert "TECHNIQUE:" in detailed_report
    
    def test_report_structure_consistency(self):
        """Test that all styles produce consistent report structure"""
        case = generate_case(seed=42)
        
        for style_name in ["concise", "detailed"]:
            case.meta.radiologist_style = style_name
            report = generate_report(case)
            
            # Check required sections
            assert "TECHNIQUE:" in report
            assert "COMPARISON:" in report
            assert "FINDINGS:" in report
            assert "IMPRESSION:" in report
            
            # Check content sections
            assert "Lungs/Primary:" in report
            assert "Mediastinum/Lymph nodes:" in report
            assert "Pleura:" in report
            assert "Abdomen/Pelvis:" in report
            assert "Bones:" in report
    
    def test_style_content_differences(self):
        """Test that different styles produce different content"""
        case = generate_case(seed=42)
        
        # Generate reports with different styles
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
    
    def test_feature_text_canonical_mapping(self):
        """Test that feature_text produces canonical, de-duplicated features"""
        # Test with duplicate features
        features = ["spiculation", "spiculation", "cavitation"]
        result = feature_text(features)
        
        # Should only contain each feature once
        assert result.count("spiculated margins") == 1
        assert result.count("internal cavitation") == 1
        
        # Test with empty features
        result = feature_text([])
        assert result == "smooth margins"
        
        # Test with unknown features
        features = ["spiculation", "unknown_feature"]
        result = feature_text(features)
        assert "spiculated margins" in result
        assert "unknown_feature" not in result
    
    def test_node_phrase_pathology_semantics(self):
        """Test that node_phrase correctly identifies pathologic vs non-pathologic nodes"""
        # Test pathologic node (≥10mm)
        pathologic_result = node_phrase("4R", 14, style="concise")
        assert "pathologic" in pathologic_result
        
        pathologic_result = node_phrase("4R", 14, style="detailed")
        assert "Enlarged" in pathologic_result
        
        # Test non-pathologic node (<10mm)
        non_pathologic_result = node_phrase("4R", 8, style="concise")
        assert "pathologic" not in non_pathologic_result
        
        non_pathologic_result = node_phrase("4R", 8, style="detailed")
        assert "Enlarged" not in non_pathologic_result
    
    def test_style_consistency_across_sections(self):
        """Test that style is consistent across all report sections"""
        case = generate_case(seed=42)
        
        # Remove nodes to test normal mediastinum phrasing
        case.nodes = []
        
        for style_name in ["concise", "detailed"]:
            case.meta.radiologist_style = style_name
            report = generate_report(case)
            
            # Check that style-appropriate phrases appear in different sections
            if style_name == "concise":
                # Concise style should have shorter, more direct phrases
                assert "No pathologic mediastinal adenopathy" in report
            else:
                # Detailed style should have longer, more descriptive phrases
                assert "Mediastinum demonstrates normal contours" in report or "No mediastinal mass" in report
    
    def test_style_with_different_lesion_types(self):
        """Test that styles work correctly with different lesion types"""
        case = generate_case(seed=42)
        
        # Ensure case has nodes and mets for testing
        if not case.nodes:
            case.nodes = [Node(station="4R", short_axis_mm=12)]
        if not case.mets:
            case.mets = [Met(site="liver", size_mm=20)]
        
        for style_name in ["concise", "detailed"]:
            case.meta.radiologist_style = style_name
            report = generate_report(case)
            
            # Check that all lesion types are described
            if case.primary:
                assert "Lungs/Primary:" in report
            if case.nodes:
                assert "Mediastinum/Lymph nodes:" in report
            if case.mets:
                assert "Abdomen/Pelvis:" in report
    
    def test_style_with_empty_lesions(self):
        """Test that styles work correctly with empty lesion lists"""
        case = generate_case(seed=42)
        
        # Remove all lesions
        case.primary = None
        case.nodes = []
        case.mets = []
        
        for style_name in ["concise", "detailed"]:
            case.meta.radiologist_style = style_name
            report = generate_report(case)
            
            # Should still generate valid report
            assert "TECHNIQUE:" in report
            assert "FINDINGS:" in report
            assert "IMPRESSION:" in report
            
            # Should have normal findings
            assert "Clear lungs" in report
            assert "No pathologic mediastinal adenopathy" in report or "Mediastinum demonstrates normal contours" in report


if __name__ == "__main__":
    pytest.main([__file__])
