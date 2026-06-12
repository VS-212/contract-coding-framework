import os
import re
from pathlib import Path
from typing import Dict, Set, Tuple
import tree_sitter_python as tspython
from tree_sitter import Language, Parser
from ..graph.heg import HierarchicalExecutionGraph

# Initialize Python grammar
PY_LANGUAGE = Language(tspython.language())
parser = Parser(PY_LANGUAGE)

class StructuralAuditor:
    def __init__(self, heg: HierarchicalExecutionGraph, source_dir: Path):
        self.heg = heg
        self.source_dir = Path(source_dir)
        self.module_nodes: Dict[str, str] = {} # AST node text (class/func name) -> M-* ID
        self.empirical_edges: Set[Tuple[str, str]] = set() # (M-A, M-B)
        
    def audit(self) -> Dict[str, any]:
        """Perform structural alignment and calculate Structural Integrity."""
        self._extract_anchors()
        self._extract_dependencies()
        return self._calculate_metrics()

    def _extract_anchors(self):
        """Finds all # @contract: M-* anchors and maps them to functions/classes."""
        anchor_pattern = re.compile(r"#\s*@contract:\s*(M-[A-Z0-9\-]+)")
        
        for py_file in self.source_dir.rglob("*.py"):
            with open(py_file, "r", encoding="utf-8") as f:
                code = f.read()
                
            tree = parser.parse(bytes(code, "utf8"))
            
            # Simple traversal to find comments followed by class/function definitions
            cursor = tree.walk()
            
            # Since tree-sitter AST navigation in Python can be complex for comments,
            # we can use a regex fallback for finding anchors, but let's do a fast block analysis.
            lines = code.split("\n")
            current_anchor = None
            
            for i, line in enumerate(lines):
                match = anchor_pattern.search(line)
                if match:
                    current_anchor = match.group(1)
                elif current_anchor and (line.strip().startswith("class ") or line.strip().startswith("def ")):
                    # Extract the name
                    parts = line.strip().split()
                    name = parts[1].split("(")[0].split(":")[0]
                    self.module_nodes[name] = current_anchor
                    current_anchor = None

    def _extract_dependencies(self):
        """Scans code for function/class calls to map empirical edges."""
        # Simple heuristic: if code belonging to M-A mentions the name of M-B's node, it's a dependency.
        for py_file in self.source_dir.rglob("*.py"):
            with open(py_file, "r", encoding="utf-8") as f:
                code = f.read()
                
            tree = parser.parse(bytes(code, "utf8"))
            
            # We'll use a regex for simplicity in this prototype:
            # For each module node, if its name appears in the code of another anchored block.
            # To do this accurately, we just check if node A's code contains node B's name.
            
            lines = code.split("\n")
            current_anchor = None
            
            anchor_pattern = re.compile(r"#\s*@contract:\s*(M-[A-Z0-9\-]+)")
            
            for line in lines:
                match = anchor_pattern.search(line)
                if match:
                    current_anchor = match.group(1)
                elif current_anchor:
                    for target_name, target_module in self.module_nodes.items():
                        if target_module != current_anchor:
                            # If the line contains a call to target_name
                            if re.search(r'\b' + re.escape(target_name) + r'\b', line):
                                self.empirical_edges.add((current_anchor, target_module))

    def _calculate_metrics(self) -> Dict[str, any]:
        theoretical_edges = set()
        for dep in self.heg.contract.topology:
            theoretical_edges.add((dep.source, dep.target))
            
        matching_edges = self.empirical_edges.intersection(theoretical_edges)
        missing_edges = theoretical_edges - self.empirical_edges
        forbidden_edges = self.empirical_edges - theoretical_edges
        
        total_theoretical = len(theoretical_edges) if theoretical_edges else 1
        
        # Penalize for missing and forbidden edges
        penalties = len(missing_edges) + len(forbidden_edges)
        score = max(0.0, 1.0 - (penalties / total_theoretical))
        
        return {
            "structural_integrity": score,
            "theoretical_edges": list(theoretical_edges),
            "empirical_edges": list(self.empirical_edges),
            "missing_edges": list(missing_edges),
            "forbidden_edges": list(forbidden_edges)
        }
