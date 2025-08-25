from synrad_lung.generator import generate_case, generate_report

def test_basic():
    c = generate_case(seed=123)
    r = generate_report(c)
    assert 'FINDINGS:' in r and 'IMPRESSION:' in r
