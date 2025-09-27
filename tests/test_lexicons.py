import sys
from pathlib import Path
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from synthrad.lexicons import (
    LOBES, SIDE_FROM_LOBE, NODE_STATIONS, STATION_METADATA, MET_SITES,
    RADIOLOGIST_STYLES, FEATURE_CANON, feature_text, station_label,
    mm_desc, node_phrase, fmt_mm, compare_size, recist_overall_response,
    percist_summary, pick, make_rng
)

class TestLexiconsData:
    """Test data structures and constants in lexicons.py"""
    
    def test_lobes_constant(self):
        """Test LOBES contains expected lung lobes"""
        expected_lobes = ["RUL", "RML", "RLL", "LUL", "LLL"]
        assert LOBES == expected_lobes
        assert len(LOBES) == 5
    
    def test_side_from_lobe_mapping(self):
        """Test SIDE_FROM_LOBE mapping is complete and correct"""
        expected_mapping = {
            "RUL": "right upper lobe",
            "RML": "right middle lobe", 
            "RLL": "right lower lobe",
            "LUL": "left upper lobe",
            "LLL": "left lower lobe"
        }
        assert SIDE_FROM_LOBE == expected_mapping
        # Ensure all lobes are covered
        for lobe in LOBES:
            assert lobe in SIDE_FROM_LOBE
    
    def test_node_stations_completeness(self):
        """Test NODE_STATIONS contains expected thoracic stations"""
        expected_stations = [
            "1R", "1L", "2R", "2L", "3A", "3P", "4R", "4L", "5", "6", "7", "8", "9",
            "10R", "10L", "11R", "11L", "12R", "12L"
        ]
        assert set(NODE_STATIONS) == set(expected_stations)
        assert len(NODE_STATIONS) == 19  # Updated to match actual count
    
    def test_station_metadata_coverage(self):
        """Test STATION_METADATA has labels and groups for key stations"""
        key_stations = ["2R", "4R", "7", "10R", "11R"]
        for station in key_stations:
            assert station in STATION_METADATA
            meta = STATION_METADATA[station]
            assert "label" in meta
            assert "group" in meta
            assert meta["group"] in ["N1", "N2"]
    
    def test_met_sites_completeness(self):
        """Test MET_SITES contains expected metastatic sites"""
        expected_sites = [
            "adrenal_right", "adrenal_left", "liver", "bone", "brain",
            "contralateral_lung", "pleura", "peritoneum", "omentum", "retroperitoneal_nodes"
        ]
        assert set(MET_SITES) == set(expected_sites)
    
    def test_radiologist_styles_structure(self):
        """Test RADIOLOGIST_STYLES has expected structure"""
        assert "concise" in RADIOLOGIST_STYLES
        assert "detailed" in RADIOLOGIST_STYLES
        assert len(RADIOLOGIST_STYLES) == 2
        
        # Test each style has required keys
        required_keys = [
            "normal_mediastinum", "normal_pleura", "normal_abdomen", "normal_bones",
            "primary_lesion_phrases", "node_phrases", "metastasis_phrases"
        ]
        for style_name, style_dict in RADIOLOGIST_STYLES.items():
            for key in required_keys:
                assert key in style_dict
                assert isinstance(style_dict[key], list)
                assert len(style_dict[key]) > 0
    
    def test_feature_canon_completeness(self):
        """Test FEATURE_CANON has canonical mappings for all features"""
        expected_features = [
            "spiculation", "cavitation", "pleural_inv_suspected", 
            "chest_wall_invasion", "atelectasis"
        ]
        for feature in expected_features:
            assert feature in FEATURE_CANON
            assert isinstance(FEATURE_CANON[feature], str)
            assert len(FEATURE_CANON[feature]) > 0


class TestLexiconsFunctions:
    """Test functions in lexicons.py"""
    
    def test_feature_text_basic(self):
        """Test feature_text function with various inputs"""
        # Test with features
        features = ["spiculation", "cavitation"]
        result = feature_text(features)
        assert "spiculated margins" in result
        assert "internal cavitation" in result
        
        # Test with empty list
        result = feature_text([])
        assert result == "smooth margins"
        
        # Test with duplicate features (should deduplicate)
        features = ["spiculation", "spiculation", "cavitation"]
        result = feature_text(features)
        assert result.count("spiculated margins") == 1
        
        # Test with unknown feature (should be ignored)
        features = ["spiculation", "unknown_feature"]
        result = feature_text(features)
        assert "spiculated margins" in result
        assert "unknown_feature" not in result
    
    def test_station_label_function(self):
        """Test station_label function returns correct labels and groups"""
        # Test known station
        label, group = station_label("4R")
        assert "paratracheal" in label.lower()
        assert group == "N2"
        
        # Test another known station
        label, group = station_label("11R")
        assert "interlobar" in label.lower()
        assert group == "N1"
        
        # Test unknown station (should have defaults)
        label, group = station_label("99X")
        assert "station 99X" in label
        assert group == "N?"
    
    def test_mm_desc_function(self):
        """Test mm_desc function for size descriptions"""
        # Test subcentimeter
        assert mm_desc(8) == "subcentimeter"
        assert mm_desc(9) == "subcentimeter"
        
        # Test mm format
        assert mm_desc(10) == "10 mm"
        assert mm_desc(15) == "15 mm"
        assert mm_desc(25) == "25 mm"
    
    def test_node_phrase_concise_style(self):
        """Test node_phrase function with concise style"""
        # Test pathologic node
        result = node_phrase("4R", 14, style="concise")
        assert "4R node" in result
        assert "14 mm" in result
        assert "short axis" in result
        assert "pathologic" in result
        
        # Test subcentimeter node
        result = node_phrase("11L", 8, style="concise")
        assert "11L node" in result
        assert "subcentimeter" in result
        assert "pathologic" not in result
    
    def test_node_phrase_detailed_style(self):
        """Test node_phrase function with detailed style"""
        # Test pathologic node
        result = node_phrase("4R", 14, style="detailed")
        assert "Enlarged" in result
        assert "paratracheal" in result
        assert "(4R)" in result
        assert "14 mm" in result
        
        # Test subcentimeter node
        result = node_phrase("11L", 8, style="detailed")
        assert "Enlarged" not in result
        assert "interlobar" in result
        assert "subcentimeter" in result
    
    def test_node_phrase_style_aliases(self):
        """Test node_phrase function with style aliases"""
        # Test aliases map to correct styles
        concise_result = node_phrase("4R", 14, style="clinical")
        detailed_result = node_phrase("4R", 14, style="academic")
        
        # Both should be different from each other
        assert concise_result != detailed_result
        
        # Clinical should be concise style
        assert "4R node" in concise_result
        
        # Academic should be detailed style  
        assert "Enlarged" in detailed_result
    
    def test_fmt_mm_function(self):
        """Test fmt_mm function for measurement formatting"""
        # Test mm format
        assert fmt_mm(8) == "8 mm"
        assert fmt_mm(15) == "15 mm"
        assert fmt_mm(99) == "99 mm"
        
        # Test cm format
        assert fmt_mm(100) == "10.0 cm"
        assert fmt_mm(150) == "15.0 cm"
        assert fmt_mm(250) == "25.0 cm"
    
    def test_compare_size_function(self):
        """Test compare_size function for size comparisons"""
        # Test baseline
        result = compare_size(25, None)
        assert "baseline measurement" in result
        
        # Test stable (small change)
        result = compare_size(25, 24)
        assert "stable" in result
        assert "now 25 mm" in result
        assert "was 24 mm" in result
        assert "Δ +1 mm" in result
        
        # Test increased (large change)
        result = compare_size(30, 20)
        assert "increased" in result
        assert "Δ +10 mm" in result
        assert "+50%" in result
        
        # Test decreased (large change)
        result = compare_size(15, 25)
        assert "decreased" in result
        assert "Δ -10 mm" in result
        assert "-40%" in result
    
    def test_recist_overall_response_function(self):
        """Test recist_overall_response function"""
        # Test baseline
        result = recist_overall_response(50, None, False, False)
        assert "Baseline" in result or "Progressive disease" in result
        
        # Test new lesions
        result = recist_overall_response(50, 40, False, True)
        assert "Progressive disease (new lesions)" in result
        
        # Test partial response
        result = recist_overall_response(25, 50, False, False)
        assert "Partial response" in result
        
        # Test stable disease
        result = recist_overall_response(45, 50, False, False)
        assert "Stable disease" in result
        
        # Test progressive disease
        result = recist_overall_response(60, 50, False, False)
        assert "Progressive disease" in result
    
    def test_percist_summary_function(self):
        """Test percist_summary function"""
        # Test baseline
        result = percist_summary(5.2, None, False)
        assert "Baseline metabolic assessment" in result
        
        # Test new lesions
        result = percist_summary(5.2, 4.8, True)
        assert "Progressive metabolic disease (new FDG-avid lesions)" in result
        
        # Test partial metabolic response
        result = percist_summary(3.0, 5.0, False)
        assert "Partial metabolic response" in result
        
        # Test stable metabolic disease
        result = percist_summary(4.8, 5.0, False)
        assert "Stable metabolic disease" in result
        
        # Test progressive metabolic disease
        result = percist_summary(7.0, 5.0, False)
        assert "Progressive metabolic disease" in result
    
    def test_pick_function(self):
        """Test pick function for random selection"""
        seq = ["a", "b", "c"]
        
        # Test with default random
        result = pick(seq)
        assert result in seq
        
        # Test with custom RNG
        rng = make_rng(42)
        result1 = pick(seq, rng)
        result2 = pick(seq, rng)
        # Should be deterministic with same seed
        rng2 = make_rng(42)
        result3 = pick(seq, rng2)
        assert result1 == result3
    
    def test_make_rng_function(self):
        """Test make_rng function for reproducible random number generation"""
        # Test without seed
        rng1 = make_rng()
        rng2 = make_rng()
        # Should be different
        assert rng1.random() != rng2.random()
        
        # Test with seed
        rng1 = make_rng(42)
        rng2 = make_rng(42)
        # Should be identical
        assert rng1.random() == rng2.random()
        
        # Test multiple calls with same seed produce same first value
        rng1 = make_rng(123)
        rng2 = make_rng(123)
        assert rng1.randint(1, 100) == rng2.randint(1, 100)


if __name__ == "__main__":
    pytest.main([__file__])
