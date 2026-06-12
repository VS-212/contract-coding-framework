import re
from pathlib import Path
from typing import Dict, List, Optional
import tree_sitter_python as tspython
from tree_sitter import Language, Parser

# Initialize Python grammar
PY_LANGUAGE = Language(tspython.language())
parser = Parser(PY_LANGUAGE)

def generate_node_skeleton(node, get_node_text) -> str:
    """
    Given a function_definition or class_definition node, returns a string skeleton.
    For a function: def name(params): pass
    For a class: class Name:
                     def method1(self): pass
    """
    if node.type == "function_definition":
        body_node = None
        for child in node.children:
            if child.type == "block":
                body_node = child
                
        if body_node:
            # The signature is everything before the block
            sig_part = get_node_text(node)[:body_node.start_byte - node.start_byte].rstrip()
            if not sig_part.endswith(":"):
                sig_part += ":"
            return f"{sig_part}\n    pass"
        else:
            return get_node_text(node)
            
    elif node.type == "class_definition":
        body_node = None
        for child in node.children:
            if child.type == "block":
                body_node = child
                
        if body_node:
            sig_part = get_node_text(node)[:body_node.start_byte - node.start_byte].rstrip()
            if not sig_part.endswith(":"):
                sig_part += ":"
            
            # Now extract methods inside the class body
            methods = []
            def find_methods(n):
                if n.type == "function_definition":
                    methods.append(n)
                elif n.type not in ("class_definition", "block"):
                    for c in n.children:
                        find_methods(c)
                        
            # Find methods inside the block
            for child in body_node.children:
                find_methods(child)
                
            if not methods:
                return f"{sig_part}\n    pass"
                
            skeleton_lines = [sig_part]
            for method in methods:
                method_skel = generate_node_skeleton(method, get_node_text)
                # Indent method skeleton
                indented = "\n".join("    " + line for line in method_skel.splitlines())
                skeleton_lines.append(indented)
            return "\n".join(skeleton_lines)
        else:
            return get_node_text(node)
            
    return get_node_text(node)

def extract_signatures_from_file(file_path: Path) -> Dict[str, str]:
    """
    Extracts skeletal signatures for modules annotated with # @contract: M-*.
    Returns a dictionary mapping module_id (e.g., 'M-A') to its Python signature/skeleton.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        code = f.read()
        
    tree = parser.parse(bytes(code, "utf8"))
    root_node = tree.root_node
    
    anchor_pattern = re.compile(r"#\s*@contract:\s*(M-[A-Z0-9\-]+)")
    lines = code.splitlines()
    module_skeletons: Dict[str, List[str]] = {}
    
    def get_node_text(node) -> str:
        return code[node.start_byte:node.end_byte]
        
    def find_definitions(node, result_list):
        if node.type in ("function_definition", "class_definition"):
            result_list.append(node)
        for child in node.children:
            find_definitions(child, result_list)
            
    all_defs = []
    find_definitions(root_node, all_defs)
    
    # Associate definitions with comments by matching their line numbers
    for node in all_defs:
        start_line = node.start_point[0]
        anchor = None
        for offset in range(1, 4):
            prev_idx = start_line - offset
            if prev_idx >= 0:
                line_content = lines[prev_idx]
                match = anchor_pattern.search(line_content)
                if match:
                    anchor = match.group(1)
                    break
                stripped = line_content.strip()
                if stripped and not stripped.startswith("#"):
                    break
        
        if anchor:
            skeleton = generate_node_skeleton(node, get_node_text)
            if anchor not in module_skeletons:
                module_skeletons[anchor] = []
            module_skeletons[anchor].append(f"# @contract: {anchor}\n{skeleton}")
            
    return {k: "\n\n".join(v) for k, v in module_skeletons.items()}

def extract_signatures_from_dir(source_dir: Path) -> Dict[str, str]:
    """
    Scans a directory of Python files and returns a dictionary of signatures for all annotated modules.
    """
    all_signatures = {}
    source_path = Path(source_dir)
    if source_path.exists():
        for py_file in source_path.rglob("*.py"):
            try:
                file_sigs = extract_signatures_from_file(py_file)
                all_signatures.update(file_sigs)
            except Exception:
                pass
    return all_signatures
