from contract_coding.schema.parser import parse_contract
from contract_coding.graph.heg import HierarchicalExecutionGraph

contract = parse_contract('api.contract.yaml')
heg = HierarchicalExecutionGraph(contract).build()

print("Execution Layers:")
for i, layer in enumerate(heg.get_execution_layers()):
    print(f"Layer {i}: {layer}")

print("\nMermaid:")
print(heg.to_mermaid())
