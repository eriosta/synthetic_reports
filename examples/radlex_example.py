#!/usr/bin/env python3
"""
Example script demonstrating basic RadLex integration usage.
Shows how to use RadLex service, lexicons, and configuration.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

def basic_radlex_example():
    """Basic example of RadLex service usage."""
    
    print("RadLex Basic Example")
    print("=" * 30)
    
    try:
        from synthrad.radlex_service import get_radlex_service
        from synthrad.radlex_lexicons import get_radlex_lexicons
        
        # Get RadLex service
        service = get_radlex_service()
        
        # Annotate some medical text
        text = "There is a pulmonary nodule in the right upper lobe with associated lymphadenopathy."
        print(f"Original text: {text}")
        
        annotations = service.annotate_text(text)
        print(f"Found {len(annotations)} RadLex annotations:")
        
        for i, annotation in enumerate(annotations, 1):
            print(f"  {i}. '{annotation['match_text']}' -> '{annotation['class_label']}'")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def enhanced_lexicons_example():
    """Example of using enhanced lexicons."""
    
    print("\nEnhanced Lexicons Example")
    print("=" * 35)
    
    try:
        from synthrad.radlex_lexicons import get_radlex_lexicons
        
        # Get enhanced lexicons
        lexicons = get_radlex_lexicons()
        
        # Get enhanced terms
        terms = {
            "nodule": lexicons.get_lung_finding_term("nodule"),
            "mass": lexicons.get_lung_finding_term("mass"),
            "effusion": lexicons.get_pleural_term("effusion"),
            "artifact": lexicons.get_artifact_term("motion")
        }
        
        print("Enhanced medical terms:")
        for original, enhanced in terms.items():
            print(f"  '{original}' -> '{enhanced}'")
        
        # Enhance text
        original_text = "There is a nodule in the right upper lobe with pleural effusion."
        enhanced_text = lexicons.enhance_text_with_radlex(original_text)
        
        print(f"\nText enhancement:")
        print(f"Original: {original_text}")
        print(f"Enhanced: {enhanced_text}")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def configuration_example():
    """Example of RadLex configuration usage."""
    
    print("\nConfiguration Example")
    print("=" * 25)
    
    try:
        from synthrad.radlex_config import get_config, PREDEFINED_CONFIGS
        
        # Show available configurations
        print("Available RadLex configurations:")
        for name, config in PREDEFINED_CONFIGS.items():
            print(f"  {name}:")
            print(f"    - Enhance terminology: {config.enhance_terminology}")
            print(f"    - Enhance artifacts: {config.enhance_artifacts}")
            print(f"    - Max enhancement ratio: {config.max_enhancement_ratio}")
        
        # Get a specific configuration
        config = get_config("conservative")
        print(f"\nConservative config:")
        print(f"  - Rate limit per second: {config.rate_limit_per_second}")
        print(f"  - Rate limit per minute: {config.rate_limit_per_minute}")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def search_example():
    """Example of searching RadLex concepts."""
    
    print("\nSearch Example")
    print("=" * 15)
    
    try:
        from synthrad.radlex_service import get_radlex_service
        
        service = get_radlex_service()
        
        # Search for concepts
        query = "pulmonary nodule"
        concepts = service.search_concepts(query, max_results=3)
        
        print(f"Search results for '{query}':")
        for i, concept in enumerate(concepts, 1):
            print(f"  {i}. {concept['label']}")
            if concept.get('definition'):
                print(f"     Definition: {concept['definition'][:100]}...")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    """Run all examples."""
    
    print("RadLex Integration Examples")
    print("=" * 40)
    
    # Check if API key is available
    if not os.environ.get("BIOPORTAL_API_KEY"):
        print("Warning: BIOPORTAL_API_KEY not set.")
        print("Get a free API key from: https://bioportal.bioontology.org/")
        print("Set it with: export BIOPORTAL_API_KEY=your_key_here")
        print("\nExamples will use fallback terminology without API key.")
    
    examples = [
        ("Basic Service", basic_radlex_example),
        ("Enhanced Lexicons", enhanced_lexicons_example),
        ("Configuration", configuration_example),
        ("Search", search_example)
    ]
    
    for name, example_func in examples:
        try:
            success = example_func()
            if success:
                print(f"✓ {name} example completed successfully")
            else:
                print(f"✗ {name} example failed")
        except Exception as e:
            print(f"✗ {name} example crashed: {e}")
    
    print("\n" + "=" * 40)
    print("Examples completed!")
    print("\nNext steps:")
    print("1. Import and use get_radlex_lexicons() in your generator")
    print("2. Configure rate limiting for your use case")
    print("3. Test with different enhancement levels")

if __name__ == "__main__":
    main()

