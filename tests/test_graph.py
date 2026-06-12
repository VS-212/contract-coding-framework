import pytest
from contract_coding.schema.parser import parse_contract
from contract_coding.graph.heg import HierarchicalExecutionGraph

def test_heg_dag_generation():
    yaml_content = """
    version: "1.0"
    intent: "Test"
    modules:
      - name: "M-A"
        description: ""
      - name: "M-B"
        description: ""
      - name: "M-C"
        description: ""
    topology:
      - source: "M-A"
        target: "M-B"
      - source: "M-B"
        target: "M-C"
    """
    contract = parse_contract(yaml_content)
    heg = HierarchicalExecutionGraph(contract).build()
    
    layers = heg.get_execution_layers()
    assert len(layers) == 3
    # Target C should be executed first (Layer 0) since B depends on C, and A depends on B
    assert 'M-C' in layers[0]
    assert 'M-B' in layers[1]
    assert 'M-A' in layers[2]
    
    # Test execution packets
    packets = heg.get_execution_packets()
    assert len(packets) == 3
    assert packets[0][0].target_node == 'M-C'

def test_heg_cyclic_dependencies():
    yaml_content = """
    version: "1.0"
    intent: "Test cyclic"
    modules:
      - name: "M-A"
        description: ""
      - name: "M-B"
        description: ""
      - name: "M-C"
        description: ""
      - name: "M-D"
        description: ""
    topology:
      - source: "M-A"
        target: "M-B"
      - source: "M-B"
        target: "M-C"
      - source: "M-C"
        target: "M-A"
      - source: "M-C"
        target: "M-D"
    """
    contract = parse_contract(yaml_content)
    heg = HierarchicalExecutionGraph(contract).build()
    
    layers = heg.get_execution_layers()
    assert len(layers) == 2
    assert 'M-D' in layers[0]
    assert any(node.startswith("CohesionNode") for node in layers[1])

def test_heg_context_engineering_signatures(tmp_path):
    # Create mock python code with anchors
    code_dir = tmp_path / "src"
    code_dir.mkdir()
    
    # M-B defines a function
    b_code = """
# @contract: M-B
def calculate_sum(a: int, b: int) -> int:
    # A long complex implementation here
    result = a + b
    return result
"""
    (code_dir / "b_module.py").write_text(b_code)
    
    # Contract: M-A depends on M-B
    yaml_content = """
    version: "1.0"
    intent: "Test signatures"
    modules:
      - name: "M-A"
        description: ""
      - name: "M-B"
        description: ""
    topology:
      - source: "M-A"
        target: "M-B"
    """
    contract = parse_contract(yaml_content)
    heg = HierarchicalExecutionGraph(contract).build()
    
    # Get execution packets with signatures
    layers = heg.get_execution_packets(source_dir=code_dir)
    
    # Layer 0 is M-B (target)
    # Layer 1 is M-A (depends on M-B)
    assert len(layers) == 2
    
    # Packet for M-A should have M-B's skeleton signature
    m_a_packet = layers[1][0]
    assert m_a_packet.target_node == "M-A"
    assert "M-B" in m_a_packet.dependency_signatures
    
    # Verify the signature is skeletal (contains pass)
    sig_content = m_a_packet.dependency_signatures["M-B"]
    assert "def calculate_sum(a: int, b: int) -> int:" in sig_content
    assert "pass" in sig_content
    assert "result = a + b" not in sig_content # Full code is hidden

def test_contract_refactoring_guide():
    from contract_coding.graph.refactor import ContractRefactorer
    
    yaml_content = """
    version: "1.0"
    intent: "Test cyclic refactoring"
    modules:
      - name: "M-A"
        description: "Module A"
      - name: "M-B"
        description: "Module B"
    topology:
      - source: "M-A"
        target: "M-B"
      - source: "M-B"
        target: "M-A"
    """
    contract = parse_contract(yaml_content)
    refactorer = ContractRefactorer(contract)
    reports = refactorer.analyze_cycles()
    
    assert len(reports) == 1
    report = reports[0]
    assert "M-A" in report["modules"]
    assert "M-B" in report["modules"]
    assert ("M-A", "M-B") in report["edges"]
    assert ("M-B", "M-A") in report["edges"]
    
    # Must contain recommendations
    assert len(report["recommendations"]) > 0
    rec_types = [rec["type"] for rec in report["recommendations"]]
    assert "INTERFACE_EXTRACTION" in rec_types
    assert "DEPENDENCY_INVERSION" in rec_types

def test_differential_heg_audit(tmp_path):
    from contract_coding.audit.structural import StructuralAuditor
    
    # Create code directory
    code_dir = tmp_path / "src"
    code_dir.mkdir()
    
    a_code = """
# @contract: M-A
def a_func():
    b_func()
"""
    b_code = """
# @contract: M-B
def b_func():
    pass
"""
    (code_dir / "a.py").write_text(a_code)
    (code_dir / "b.py").write_text(b_code)
    
    yaml_content = """
    version: "1.0"
    intent: "Test"
    modules:
      - name: "M-A"
        description: ""
      - name: "M-B"
        description: ""
    topology:
      - source: "M-A"
        target: "M-B"
    """
    contract = parse_contract(yaml_content)
    heg = HierarchicalExecutionGraph(contract).build()
    
    # Audit 1 (Generates cache)
    auditor = StructuralAuditor(heg, code_dir)
    res1 = auditor.audit()
    assert res1["structural_integrity"] == 1.0
    
    cache_path = code_dir / ".contract-cache.json"
    assert cache_path.exists()
    
    # Modify a file
    a_code_mod = """
# @contract: M-A
def a_func():
    # still calls b_func
    b_func()
    pass
"""
    (code_dir / "a.py").write_text(a_code_mod)
    
    # Audit 2 (Should load B from cache, re-audit A)
    auditor2 = StructuralAuditor(heg, code_dir)
    res2 = auditor2.audit()
    assert res2["structural_integrity"] == 1.0


