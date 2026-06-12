import networkx as nx
from typing import List, Dict, Any
from ..schema.contract import LanguageContract

class ContractRefactorer:
    def __init__(self, contract: LanguageContract):
        self.contract = contract
        self.graph = nx.DiGraph()
        self._build_graph()
        
    def _build_graph(self):
        for module in self.contract.modules:
            self.graph.add_node(module.name, data=module)
        for dep in self.contract.topology:
            if dep.source in self.graph and dep.target in self.graph:
                self.graph.add_edge(dep.source, dep.target)
                
    def analyze_cycles(self) -> List[Dict[str, Any]]:
        """
        Detects cycles in the contract topology and generates refactoring recommendations.
        """
        sccs = list(nx.strongly_connected_components(self.graph))
        cycle_reports = []
        
        for scc in sccs:
            if len(scc) > 1:
                nodes = list(scc)
                # Find all edges forming the cycle
                edges = []
                for u in nodes:
                    for v in self.graph.successors(u):
                        if v in scc:
                            edges.append((u, v))
                            
                recommendations = []
                
                # Recommendation 1: Interface Extraction
                recommendations.append({
                    "type": "INTERFACE_EXTRACTION",
                    "title": "Extract Common Interface/Types",
                    "description": f"Extract shared structures/types utilized by both {', '.join(nodes)} into a new leaf module (e.g., M-{nodes[0][2:]}-SHARED) that both can depend on."
                })
                
                # Recommendation 2: Dependency Inversion / Event-Driven IoC
                for u, v in edges:
                    recommendations.append({
                        "type": "DEPENDENCY_INVERSION",
                        "title": f"Invert Dependency {u} -> {v}",
                        "description": f"Decouple {u} from {v} by introducing an event/listener boundary so {v} publishes notifications and {u} listens, removing direct calls."
                    })
                    
                # Recommendation 3: Module Merge
                recommendations.append({
                    "type": "MODULE_MERGE",
                    "title": f"Merge Modules {', '.join(nodes)}",
                    "description": f"If these components represent a single domain partition, combine them into a single module to dissolve the cyclic dependency."
                })
                
                cycle_reports.append({
                    "modules": sorted(nodes),
                    "edges": sorted(edges),
                    "recommendations": recommendations
                })
                
        return cycle_reports
