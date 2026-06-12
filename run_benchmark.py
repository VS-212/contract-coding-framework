import os
from pathlib import Path
from contract_coding.schema.parser import parse_contract
from contract_coding.graph.heg import HierarchicalExecutionGraph
from contract_coding.audit.structural import StructuralAuditor

# 1. Simple API (Perfect)
YAML_1 = """
version: "1.0"
intent: "Simple API"
modules:
  - name: "M-CTRL"
    description: "Controller"
  - name: "M-SVC"
    description: "Service"
topology:
  - source: "M-CTRL"
    target: "M-SVC"
"""
CODE_1 = """
# @contract: M-SVC
def svc_func(): pass

# @contract: M-CTRL
def ctrl_func():
    svc_func()
"""

# 2. Linear (Missing Edge)
YAML_2 = """
version: "1.0"
intent: "Linear"
modules:
  - name: "M-A"
    description: ""
  - name: "M-B"
    description: ""
topology:
  - source: "M-A"
    target: "M-B"
"""
CODE_2 = """
# @contract: M-B
def b_func(): pass

# @contract: M-A
def a_func():
    # Forgot to call the dependency
    pass
"""

# 3. Forbidden Edge (Drift)
YAML_3 = """
version: "1.0"
intent: "Forbidden"
modules:
  - name: "M-A"
    description: ""
  - name: "M-B"
    description: ""
topology:
  - source: "M-A"
    target: "M-B"
"""
CODE_3 = """
# @contract: M-B
def b_func():
    a_func() # Forbidden edge!

# @contract: M-A
def a_func():
    b_func()
"""

# 4. Independent (Perfect)
YAML_4 = """
version: "1.0"
intent: "Independent"
modules:
  - name: "M-A"
    description: ""
  - name: "M-B"
    description: ""
topology: []
"""
CODE_4 = """
# @contract: M-A
def a_func(): pass

# @contract: M-B
def b_func(): pass
"""

# 5. Triangle (Perfect)
YAML_5 = """
version: "1.0"
intent: "Triangle"
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
  - source: "M-A"
    target: "M-C"
"""
CODE_5 = """
# @contract: M-C
def c_func(): pass

# @contract: M-B
def b_func():
    c_func()

# @contract: M-A
def a_func():
    b_func()
    c_func()
"""

BENCHMARKS = [
    ("SimpleAPI", YAML_1, CODE_1),
    ("MissingEdge", YAML_2, CODE_2),
    ("ForbiddenEdge", YAML_3, CODE_3),
    ("Independent", YAML_4, CODE_4),
    ("Triangle", YAML_5, CODE_5),
]

def run():
    base_dir = Path("benchmarks/greenfield5")
    contracts_dir = base_dir / "contracts"
    mock_dir = base_dir / "mock_code"
    
    contracts_dir.mkdir(parents=True, exist_ok=True)
    mock_dir.mkdir(parents=True, exist_ok=True)
    
    total_score = 0.0
    
    print("🚀 Running Greenfield-5 Benchmark...\n")
    
    for i, (name, yaml_content, code_content) in enumerate(BENCHMARKS):
        yaml_path = contracts_dir / f"{name}.yaml"
        code_dir = mock_dir / name
        code_dir.mkdir(exist_ok=True)
        code_path = code_dir / "main.py"
        
        yaml_path.write_text(yaml_content)
        code_path.write_text(code_content)
        
        contract = parse_contract(yaml_path)
        heg = HierarchicalExecutionGraph(contract).build()
        
        auditor = StructuralAuditor(heg, code_dir)
        results = auditor.audit()
        
        score = results["structural_integrity"] * 100
        total_score += score
        
        print(f"[{i+1}/5] {name}: {score:.1f}%")
        if score < 100:
            if results["missing_edges"]:
                print(f"   Missing: {results['missing_edges']}")
            if results["forbidden_edges"]:
                print(f"   Forbidden: {results['forbidden_edges']}")
                
    avg_score = total_score / len(BENCHMARKS)
    print(f"\n📊 Greenfield-5 Average Structural Integrity: {avg_score:.1f}%")

if __name__ == "__main__":
    run()
