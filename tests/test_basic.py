import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from synthrad.generator import generate_case, generate_report

def test_basic():
    c = generate_case(seed=123)
    r = generate_report(c)
    assert 'FINDINGS:' in r and 'IMPRESSION:' in r
