"""
RadLex-enhanced lexicons for synthetic radiology reports.
Provides realistic medical terminology from RadLex ontology.
"""

import random
from typing import Dict, List, Optional, Set
from .radlex_service import get_radlex_service

# Pre-curated RadLex concepts for common radiology findings
RADLEX_CONCEPTS = {
    "lung_findings": {
        "nodule": [
            "Pulmonary nodule",
            "Solitary pulmonary nodule", 
            "Ground glass nodule",
            "Solid nodule",
            "Part-solid nodule"
        ],
        "mass": [
            "Pulmonary mass",
            "Lung mass",
            "Parenchymal mass"
        ],
        "opacity": [
            "Ground glass opacity",
            "Consolidation",
            "Pulmonary infiltrate",
            "Airspace opacity"
        ],
        "atelectasis": [
            "Atelectasis",
            "Volume loss",
            "Collapse"
        ]
    },
    "lymph_nodes": {
        "enlarged": [
            "Lymphadenopathy",
            "Enlarged lymph node",
            "Pathologically enlarged lymph node"
        ],
        "stations": {
            "2R": "Right upper paratracheal lymph node",
            "4R": "Right lower paratracheal lymph node", 
            "2L": "Left upper paratracheal lymph node",
            "4L": "Left lower paratracheal lymph node",
            "7": "Subcarinal lymph node",
            "10R": "Right hilar lymph node",
            "10L": "Left hilar lymph node",
            "11R": "Right interlobar lymph node",
            "11L": "Left interlobar lymph node"
        }
    },
    "pleura": {
        "effusion": [
            "Pleural effusion",
            "Pleural fluid",
            "Pleural collection"
        ],
        "thickening": [
            "Pleural thickening",
            "Pleural plaque"
        ],
        "nodule": [
            "Pleural nodule",
            "Pleural-based mass"
        ]
    },
    "mediastinum": {
        "normal": [
            "Mediastinum within normal limits",
            "No mediastinal mass",
            "Mediastinal contours normal"
        ],
        "mass": [
            "Mediastinal mass",
            "Mediastinal widening"
        ]
    },
    "artifacts": {
        "motion": [
            "Motion artifact",
            "Respiratory motion",
            "Patient motion"
        ],
        "beam_hardening": [
            "Beam hardening artifact",
            "Streak artifact"
        ],
        "partial_volume": [
            "Partial volume artifact",
            "Volume averaging"
        ]
    }
}

class RadLexEnhancedLexicons:
    """Enhanced lexicons with RadLex integration."""
    
    def __init__(self, use_radlex: bool = True, cache_file: Optional[str] = None, 
                 rate_limit_per_second: float = 1.0, rate_limit_per_minute: int = 60):
        self.use_radlex = use_radlex
        self.radlex_service = None
        self.cache_file = cache_file
        
        if use_radlex:
            try:
                self.radlex_service = get_radlex_service(
                    cache_file=cache_file,
                    rate_limit_per_second=rate_limit_per_second,
                    rate_limit_per_minute=rate_limit_per_minute
                )
            except Exception as e:
                print(f"Warning: RadLex service unavailable: {e}")
                self.use_radlex = False
    
    def get_lung_finding_term(self, finding_type: str, fallback: str = None) -> str:
        """Get RadLex term for lung finding."""
        if self.use_radlex and self.radlex_service:
            try:
                # Try to get RadLex concept
                concept = self.radlex_service.get_concept_by_text(finding_type)
                if concept:
                    return concept["class_label"]
            except Exception:
                pass
        
        # Fallback to curated terms
        terms = RADLEX_CONCEPTS["lung_findings"].get(finding_type, [])
        if terms:
            return random.choice(terms)
        
        return fallback or finding_type
    
    def get_lymph_node_term(self, station: str, size_mm: int) -> str:
        """Get RadLex term for lymph node description."""
        if self.use_radlex and self.radlex_service:
            try:
                # Try to get RadLex concept for lymphadenopathy
                concept = self.radlex_service.get_concept_by_text("lymphadenopathy")
                if concept:
                    base_term = concept["class_label"]
                    station_desc = RADLEX_CONCEPTS["lymph_nodes"]["stations"].get(station, station)
                    return f"{station_desc} {base_term} measuring {size_mm} mm"
            except Exception:
                pass
        
        # Fallback to curated terms
        station_desc = RADLEX_CONCEPTS["lymph_nodes"]["stations"].get(station, station)
        if size_mm >= 10:
            term = random.choice(RADLEX_CONCEPTS["lymph_nodes"]["enlarged"])
        else:
            term = "Subcentimeter lymph node"
        
        return f"{station_desc} {term} measuring {size_mm} mm"
    
    def get_pleural_term(self, finding_type: str, fallback: str = None) -> str:
        """Get RadLex term for pleural finding."""
        if self.use_radlex and self.radlex_service:
            try:
                concept = self.radlex_service.get_concept_by_text(finding_type)
                if concept:
                    return concept["class_label"]
            except Exception:
                pass
        
        terms = RADLEX_CONCEPTS["pleura"].get(finding_type, [])
        if terms:
            return random.choice(terms)
        
        return fallback or finding_type
    
    def get_artifact_term(self, artifact_type: str) -> str:
        """Get RadLex term for imaging artifact."""
        if self.use_radlex and self.radlex_service:
            try:
                concept = self.radlex_service.get_concept_by_text(artifact_type)
                if concept:
                    return concept["class_label"]
            except Exception:
                pass
        
        terms = RADLEX_CONCEPTS["artifacts"].get(artifact_type, [])
        if terms:
            return random.choice(terms)
        
        return artifact_type
    
    def enhance_text_with_radlex(self, text: str) -> str:
        """Enhance text by replacing terms with RadLex concepts where appropriate."""
        if not self.use_radlex or not self.radlex_service:
            return text
        
        try:
            annotations = self.radlex_service.annotate_text(text)
            
            # Sort by length (longest first) to avoid partial replacements
            annotations.sort(key=lambda x: len(x["match_text"]), reverse=True)
            
            enhanced_text = text
            for annotation in annotations:
                match_text = annotation["match_text"]
                class_label = annotation["class_label"]
                
                # Only replace if the RadLex term is more specific/standard
                if len(class_label) > len(match_text) and class_label.lower() != match_text.lower():
                    enhanced_text = enhanced_text.replace(match_text, class_label)
            
            return enhanced_text
            
        except Exception as e:
            print(f"Warning: Failed to enhance text with RadLex: {e}")
            return text
    
    def get_radlex_synonyms(self, term: str) -> List[str]:
        """Get synonyms for a term from RadLex."""
        if not self.use_radlex or not self.radlex_service:
            return []
        
        try:
            concept = self.radlex_service.get_concept_by_text(term)
            if concept:
                return concept.get("synonyms", [])
        except Exception:
            pass
        
        return []
    
    def search_radlex_concepts(self, query: str, max_results: int = 5) -> List[Dict]:
        """Search for RadLex concepts."""
        if not self.use_radlex or not self.radlex_service:
            return []
        
        try:
            return self.radlex_service.search_concepts(query, max_results)
        except Exception:
            return []

# Global instance
_radlex_lexicons = None

def get_radlex_lexicons(use_radlex: bool = True, cache_file: Optional[str] = None,
                       rate_limit_per_second: float = 1.0, rate_limit_per_minute: int = 60) -> RadLexEnhancedLexicons:
    """Get or create global RadLex-enhanced lexicons instance."""
    global _radlex_lexicons
    if _radlex_lexicons is None:
        _radlex_lexicons = RadLexEnhancedLexicons(
            use_radlex, 
            cache_file,
            rate_limit_per_second=rate_limit_per_second,
            rate_limit_per_minute=rate_limit_per_minute
        )
    return _radlex_lexicons
