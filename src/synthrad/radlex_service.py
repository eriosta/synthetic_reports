"""
RadLex service for integrating medical terminology into synthetic reports.
Provides access to RadLex ontology concepts via BioPortal API.
"""

import os
import requests
import urllib.parse
import json
import time
from typing import Dict, List, Optional, Tuple, Set
from functools import lru_cache
import logging
from threading import Lock

logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter for API calls to respect BioPortal limits."""
    
    def __init__(self, calls_per_second: float = 1.0, calls_per_minute: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            calls_per_second: Maximum calls per second (default: 1.0 for free BioPortal)
            calls_per_minute: Maximum calls per minute (default: 60 for free BioPortal)
        """
        self.calls_per_second = calls_per_second
        self.calls_per_minute = calls_per_minute
        self.last_call_time = 0
        self.call_times = []  # Track calls for minute-based limiting
        self.lock = Lock()
    
    def wait_if_needed(self):
        """Wait if necessary to respect rate limits."""
        with self.lock:
            current_time = time.time()
            
            # Clean old call times (older than 1 minute)
            self.call_times = [t for t in self.call_times if current_time - t < 60]
            
            # Check minute-based limit
            if len(self.call_times) >= self.calls_per_minute:
                sleep_time = 60 - (current_time - self.call_times[0])
                if sleep_time > 0:
                    logger.info(f"Rate limit reached. Waiting {sleep_time:.2f} seconds...")
                    time.sleep(sleep_time)
                    current_time = time.time()
            
            # Check second-based limit
            time_since_last = current_time - self.last_call_time
            if time_since_last < (1.0 / self.calls_per_second):
                sleep_time = (1.0 / self.calls_per_second) - time_since_last
                logger.debug(f"Rate limiting: waiting {sleep_time:.3f} seconds")
                time.sleep(sleep_time)
            
            # Record this call
            self.last_call_time = time.time()
            self.call_times.append(current_time)

class RadLexService:
    """Service for interacting with RadLex ontology via BioPortal API."""
    
    def __init__(self, api_key: Optional[str] = None, cache_file: Optional[str] = None, 
                 rate_limit_per_second: float = 1.0, rate_limit_per_minute: int = 60):
        self.api_key = api_key or os.environ.get("BIOPORTAL_API_KEY")
        if not self.api_key:
            raise RuntimeError("Missing BIOPORTAL_API_KEY environment variable")
        
        self.base_url = "https://data.bioontology.org"
        self.headers = {"Authorization": f"apikey token={self.api_key}"}
        self.cache_file = cache_file
        self.rate_limiter = RateLimiter(rate_limit_per_second, rate_limit_per_minute)
        self._load_cache()
    
    def _load_cache(self):
        """Load cached RadLex concepts from file."""
        self.cache = {}
        if self.cache_file and os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    self.cache = json.load(f)
                logger.info(f"Loaded {len(self.cache)} cached RadLex concepts")
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
                self.cache = {}
    
    def _save_cache(self):
        """Save RadLex concepts to cache file."""
        if self.cache_file:
            try:
                with open(self.cache_file, 'w') as f:
                    json.dump(self.cache, f, indent=2)
                logger.info(f"Saved {len(self.cache)} RadLex concepts to cache")
            except Exception as e:
                logger.warning(f"Failed to save cache: {e}")
    
    def annotate_text(self, text: str, include_metadata: bool = True) -> List[Dict]:
        """
        Annotate text with RadLex concepts.
        
        Args:
            text: Text to annotate
            include_metadata: Whether to include prefLabel, synonyms, etc.
        
        Returns:
            List of annotation dictionaries with match_text, class_label, class_iri
        """
        # Apply rate limiting
        self.rate_limiter.wait_if_needed()
        
        try:
            params = {
                "ontologies": "RADLEX",
                "longest_only": "true",
            }
            if include_metadata:
                params["include"] = "prefLabel,synonym,definition,notation"
            
            response = requests.post(
                f"{self.base_url}/annotator",
                headers={**self.headers, "Content-Type": "application/json"},
                json={"text": text},
                params=params,
                timeout=30
            )
            response.raise_for_status()
            annotations = response.json()
            
            return self._process_annotations(annotations)
            
        except requests.RequestException as e:
            logger.error(f"RadLex API request failed: {e}")
            return []
        except Exception as e:
            logger.error(f"RadLex annotation failed: {e}")
            return []
    
    def _process_annotations(self, annotations: List[Dict]) -> List[Dict]:
        """Process raw annotations into clean format."""
        processed = []
        seen = set()
        
        for annotation in annotations:
            span = annotation.get("annotations", [{}])[0]
            match_text = span.get("text", "")
            class_info = annotation.get("annotatedClass", {})
            class_iri = class_info.get("@id")
            
            if not class_iri or not match_text:
                continue
            
            # Check cache first
            cache_key = f"{match_text}_{class_iri}"
            if cache_key in seen:
                continue
            seen.add(cache_key)
            
            # Get label from annotation or fetch it
            class_label = class_info.get("prefLabel")
            if not class_label:
                class_label = self._fetch_class_label(class_iri)
            
            if class_label:
                processed.append({
                    "match_text": match_text,
                    "class_label": class_label,
                    "class_iri": class_iri,
                    "synonyms": class_info.get("synonym", []),
                    "definition": class_info.get("definition"),
                    "notation": class_info.get("notation")
                })
        
        return processed
    
    def _fetch_class_label(self, class_iri: str) -> Optional[str]:
        """Fetch class label from RadLex API."""
        if class_iri in self.cache:
            return self.cache[class_iri]
        
        # Apply rate limiting
        self.rate_limiter.wait_if_needed()
        
        try:
            iri_enc = urllib.parse.quote(class_iri, safe="")
            url = f"{self.base_url}/ontologies/RADLEX/classes/{iri_enc}"
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 404 and class_iri.startswith("http://radlex.org"):
                # Try with www prefix - apply rate limiting for retry too
                self.rate_limiter.wait_if_needed()
                iri_enc = urllib.parse.quote(
                    class_iri.replace("http://radlex.org", "http://www.radlex.org"), 
                    safe=""
                )
                url = f"{self.base_url}/ontologies/RADLEX/classes/{iri_enc}"
                response = requests.get(url, headers=self.headers, timeout=30)
            
            response.raise_for_status()
            class_data = response.json()
            
            label = class_data.get("prefLabel") or class_data.get("label") or class_data.get("notation")
            
            if label:
                self.cache[class_iri] = label
                self._save_cache()
            
            return label
            
        except Exception as e:
            logger.warning(f"Failed to fetch label for {class_iri}: {e}")
            return None
    
    def get_concept_by_text(self, text: str) -> Optional[Dict]:
        """Get RadLex concept by searching for specific text."""
        annotations = self.annotate_text(text)
        for annotation in annotations:
            if annotation["match_text"].lower() == text.lower():
                return annotation
        return None
    
    def get_synonyms(self, concept_iri: str) -> List[str]:
        """Get synonyms for a RadLex concept."""
        # Apply rate limiting
        self.rate_limiter.wait_if_needed()
        
        try:
            iri_enc = urllib.parse.quote(concept_iri, safe="")
            url = f"{self.base_url}/ontologies/RADLEX/classes/{iri_enc}"
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            class_data = response.json()
            return class_data.get("synonym", [])
        except Exception as e:
            logger.warning(f"Failed to fetch synonyms for {concept_iri}: {e}")
            return []
    
    def search_concepts(self, query: str, max_results: int = 10) -> List[Dict]:
        """Search for RadLex concepts by query."""
        # Apply rate limiting
        self.rate_limiter.wait_if_needed()
        
        try:
            params = {
                "q": query,
                "ontologies": "RADLEX",
                "pagesize": max_results
            }
            response = requests.get(
                f"{self.base_url}/search",
                headers=self.headers,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            results = response.json()
            
            concepts = []
            for result in results.get("collection", []):
                concept = {
                    "label": result.get("prefLabel"),
                    "iri": result.get("@id"),
                    "definition": result.get("definition"),
                    "notation": result.get("notation")
                }
                if concept["label"]:
                    concepts.append(concept)
            
            return concepts
            
        except Exception as e:
            logger.error(f"RadLex search failed: {e}")
            return []

# Global service instance
_radlex_service = None

def get_radlex_service(cache_file: Optional[str] = None, 
                      rate_limit_per_second: float = 1.0, 
                      rate_limit_per_minute: int = 60) -> RadLexService:
    """Get or create global RadLex service instance."""
    global _radlex_service
    if _radlex_service is None:
        _radlex_service = RadLexService(
            cache_file=cache_file,
            rate_limit_per_second=rate_limit_per_second,
            rate_limit_per_minute=rate_limit_per_minute
        )
    return _radlex_service
