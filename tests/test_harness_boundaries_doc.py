import os
from pathlib import Path

def test_harness_boundaries_doc_exists():
    """Verify the harness interface boundaries design document file exists and is non-empty."""
    doc_path = Path("drake/.docs/architecture/harness_interface_boundaries.md")
    assert doc_path.exists(), f"Document not found at {doc_path}"
    assert doc_path.stat().st_size > 0, "Document is empty"

def test_harness_boundaries_doc_contains_required_sections():
    """Check that all mandated sections are present in the document."""
    doc_path = Path("drake/.docs/architecture/harness_interface_boundaries.md")
    content = doc_path.read_text()
    
    required_headings = [
        "Current State Analysis",
        "Proposed Trait Boundaries",
        "Adapter Surface Validation",
        "Strangler-Fig Migration Plan",
        "Anti-Patterns to Avoid",
    ]
    
    for heading in required_headings:
        assert heading in content, f"Missing heading: '{heading}'"
