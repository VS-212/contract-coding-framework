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
