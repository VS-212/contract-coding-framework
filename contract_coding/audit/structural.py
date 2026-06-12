import os
import re
import json
import hashlib
from pathlib import Path
from typing import Dict, Set, Tuple, Any
import tree_sitter_python as tspython
from tree_sitter import Language, Parser
from ..graph.heg import HierarchicalExecutionGraph

# Initialize Python grammar
PY_LANGUAGE = Language(tspython.language())
parser = Parser(PY_LANGUAGE)

def get_file_hash(path: Path) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

class StructuralAuditor:
    def __init__(self, heg: HierarchicalExecutionGraph, source_dir: Path):
        self.heg = heg
        self.source_dir = Path(source_dir)
        self.cache_path = self.source_dir / ".contract-cache.json"
        self.module_nodes: Dict[str, str] = {} # AST node text (class/func name) -> M-* ID
        self.empirical_edges: Set[Tuple[str, str]] = set() # (M-A, M-B)
        self.cache: Dict[str, Any] = {"module_nodes": {}, "files": {}}
        self.new_cache: Dict[str, Any] = {"module_nodes": {}, "files": {}}
        self._load_cache()

    def _load_cache(self):
        if self.cache_path.exists():
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
            except Exception:
                pass

    def _save_cache(self):
        try:
            self.new_cache["module_nodes"] = self.module_nodes
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self.new_cache, f, indent=2)
        except Exception:
            pass

    def audit(self) -> Dict[str, any]:
        """Perform structural alignment and calculate Structural Integrity."""
        self._extract_anchors()
        self._extract_dependencies()
        self._save_cache()
        return self._calculate_metrics()

    def _extract_anchors(self):
        """Finds all # @contract: M-* anchors and maps them to functions/classes."""
        anchor_pattern = re.compile(r"#\s*@contract:\s*(M-[A-Z0-9\-]+)")
        
        for py_file in self.source_dir.rglob("*.py"):
            if py_file.name == ".contract-cache.json":
                continue
            rel_path = str(py_file.relative_to(self.source_dir))
            
            try:
                file_hash = get_file_hash(py_file)
            except Exception:
                continue
                
            # Check cache
            cached_file = self.cache.get("files", {}).get(rel_path)
            if cached_file and cached_file.get("hash") == file_hash:
                anchors = cached_file.get("anchors", {})
                self.module_nodes.update(anchors)
                self.new_cache["files"][rel_path] = cached_file
                continue
                
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    code = f.read()
            except Exception:
                continue
                
            tree = parser.parse(bytes(code, "utf8"))
            lines = code.split("\n")
            current_anchor = None
            file_anchors = {}
            
            for i, line in enumerate(lines):
                match = anchor_pattern.search(line)
                if match:
                    current_anchor = match.group(1)
                elif current_anchor and (line.strip().startswith("class ") or line.strip().startswith("def ")):
                    parts = line.strip().split()
                    name = parts[1].split("(")[0].split(":")[0]
                    file_anchors[name] = current_anchor
                    self.module_nodes[name] = current_anchor
                    current_anchor = None
                    
            self.new_cache["files"][rel_path] = {
                "hash": file_hash,
                "anchors": file_anchors,
                "calls": []
            }

    def _extract_dependencies(self):
        """Scans code for function/class calls to map empirical edges."""
        anchor_pattern = re.compile(r"#\s*@contract:\s*(M-[A-Z0-9\-]+)")
        nodes_changed = (self.module_nodes != self.cache.get("module_nodes"))
        
        for py_file in self.source_dir.rglob("*.py"):
            if py_file.name == ".contract-cache.json":
                continue
            rel_path = str(py_file.relative_to(self.source_dir))
            
            cached_file = self.cache.get("files", {}).get(rel_path)
            if cached_file and not nodes_changed and rel_path in self.new_cache["files"]:
                if self.new_cache["files"][rel_path].get("hash") == cached_file.get("hash"):
                    calls = cached_file.get("calls", [])
                    for source, target in calls:
                        self.empirical_edges.add((source, target))
                    self.new_cache["files"][rel_path]["calls"] = calls
                    continue
            
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    code = f.read()
            except Exception:
                continue
                
            lines = code.split("\n")
            current_anchor = None
            file_calls = set()
            
            for line in lines:
                match = anchor_pattern.search(line)
                if match:
                    current_anchor = match.group(1)
                elif current_anchor:
                    for target_name, target_module in self.module_nodes.items():
                        if target_module != current_anchor:
                            if re.search(r'\b' + re.escape(target_name) + r'\b', line):
                                self.empirical_edges.add((current_anchor, target_module))
                                file_calls.add((current_anchor, target_module))
                                
            if rel_path in self.new_cache["files"]:
                self.new_cache["files"][rel_path]["calls"] = list(file_calls)

    def _calculate_metrics(self) -> Dict[str, any]:
        theoretical_edges = set()
        for dep in self.heg.contract.topology:
            theoretical_edges.add((dep.source, dep.target))
            
        matching_edges = self.empirical_edges.intersection(theoretical_edges)
        missing_edges = theoretical_edges - self.empirical_edges
        forbidden_edges = self.empirical_edges - theoretical_edges
        
        total_theoretical = len(theoretical_edges) if theoretical_edges else 1
        
        penalties = len(missing_edges) + len(forbidden_edges)
        score = max(0.0, 1.0 - (penalties / total_theoretical))
        
        return {
            "structural_integrity": score,
            "theoretical_edges": list(theoretical_edges),
            "empirical_edges": list(self.empirical_edges),
            "missing_edges": list(missing_edges),
            "forbidden_edges": list(forbidden_edges)
        }
