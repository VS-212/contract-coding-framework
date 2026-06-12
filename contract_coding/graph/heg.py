import networkx as nx
from typing import List, Dict, Set, Any
from ..schema.contract import LanguageContract

class HierarchicalExecutionGraph:
    def __init__(self, contract: LanguageContract):
        self.contract = contract
        self.raw_graph = nx.DiGraph()
        self.execution_graph = nx.DiGraph()
        self.cohesion_nodes: Dict[str, Set[str]] = {}
        
    def build(self) -> 'HierarchicalExecutionGraph':
        """Builds the HEG from the Language Contract."""
        # 1. Add all modules as nodes
        for module in self.contract.modules:
            self.raw_graph.add_node(module.name, data=module)
            
        # 2. Add dependencies as directed edges
        for dep in self.contract.topology:
            if dep.source in self.raw_graph and dep.target in self.raw_graph:
                self.raw_graph.add_edge(dep.source, dep.target, description=dep.description)
                
        # 3. Handle cyclic dependencies using Tarjan's strongly connected components
        self._condense_graph()
        
        return self
        
    def _condense_graph(self):
        """Condenses the graph by grouping strongly connected components (cycles) into cohesion nodes."""
        sccs = list(nx.strongly_connected_components(self.raw_graph))
        
        # If every SCC has length 1, it's already a DAG
        if all(len(scc) == 1 for scc in sccs):
            self.execution_graph = self.raw_graph.copy()
            return
            
        # Otherwise, build the condensation graph (which is guaranteed to be a DAG)
        cg = nx.condensation(self.raw_graph, scc=sccs)
        
        for node in cg.nodes():
            members = cg.nodes[node]['members']
            if len(members) > 1:
                group_name = f"CohesionNode({','.join(members)})"
                self.cohesion_nodes[group_name] = members
                cg.nodes[node]['name'] = group_name
            else:
                cg.nodes[node]['name'] = list(members)[0]
                
        # Re-label nodes with meaningful names
        mapping = {n: cg.nodes[n]['name'] for n in cg.nodes()}
        self.execution_graph = nx.relabel_nodes(cg, mapping)
        
    def get_execution_layers(self) -> List[List[str]]:
        """
        Returns a list of node sets. Each set represents a layer that can be
        executed in parallel. Nodes in layer N only depend on nodes in layers > N.
        Since dependencies point from source to target (source depends on target),
        target should be executed first.
        Therefore, we reverse the graph to find the execution order.
        """
        reversed_graph = self.execution_graph.reverse(copy=True)
        return list(nx.topological_generations(reversed_graph))
        
    def get_execution_packets(self) -> List[List['ExecutionPacket']]:
        from ..schema.packet import ExecutionPacket
        layers = self.get_execution_layers()
        packet_layers = []
        for layer in layers:
            packet_layer = []
            for node in layer:
                if node.startswith("CohesionNode"):
                    modules = list(self.cohesion_nodes[node])
                else:
                    modules = [node]
                
                # Default stop condition is that all V-M-* verification tests pass
                stop_conditions = [f"Pass verification for {m}" for m in modules]
                
                packet = ExecutionPacket(
                    target_node=node,
                    modules=modules,
                    stop_conditions=stop_conditions,
                    retry_budget=3
                )
                packet_layer.append(packet)
            packet_layers.append(packet_layer)
        return packet_layers
        
    def to_mermaid(self) -> str:
        """Generates a Mermaid.js flowchart representation of the execution graph."""
        lines = ["flowchart TD"]
        
        # Add nodes
        for node in self.execution_graph.nodes():
            if node.startswith("CohesionNode"):
                members = "\\n".join(self.cohesion_nodes[node])
                lines.append(f'    {node}["{node}\\n{members}"]')
            else:
                lines.append(f'    {node}["{node}"]')
                
        # Add edges
        for u, v in self.execution_graph.edges():
            lines.append(f'    {u} --> {v}')
            
        return "\n".join(lines)
