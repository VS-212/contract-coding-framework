# Contract-Coding Framework 🚀

A mathematically grounded meta-engineering framework that implements a **Single Source of Truth (SSOT)** for AI-agentic software engineering. By translating fuzzy product intents into a formal **Language Contract $\mathcal{C}$** and compiling it into a **Hierarchical Execution Graph (HEG)**, this framework coordinates autonomous code generation and performs structural alignment verification using AST parsing.

Inspired by the pioneering work in the **GRACE** methodology and **Structured Symbolic Paradigms**, this project solves the *Context-Fidelity Trade-off* and prevents *Architectural Collapse* in multi-agent systems during greenfield project creation.

---

## 📚 Theoretical Foundation

### 1. The Language Contract $\mathcal{C}$
Rather than feed LLMs raw prompt text ("vibe coding"), we compile the requirements into a formal, declarative contract:
$$\mathcal{C} = \langle \text{Intent}, \Phi_{global}, S, \mathcal{A}, T, \mathcal{V} \rangle$$
Where:
- $\text{Intent}$: High-level user goal.
- $\Phi_{global}$: Global constraints (e.g., "no cyclic dependencies").
- $S$: Approved technology stack.
- $\mathcal{A}$: **Semantic Attractors** (Modules $M_i$) capturing localized responsibilities and boundaries.
- $T$: **Topology** (directed dependencies between modules).
- $\mathcal{V}$: **Verification Plans** ($V_{M_i}$) with automated tests.

### 2. Hierarchical Execution Graph (HEG)
The topology of dependencies is built into a directed graph. Cycles are detected using Tarjan's strongly connected components algorithm and condensed into **Cohesion Nodes**. The resulting graph is a pure Directed Acyclic Graph (DAG), which is topologically sorted to produce execution layers that can be processed in parallel.

### 3. Structural Alignment Auditor $E(\mathcal{C})$
The auditor uses `tree-sitter-python` to parse AST trees of generated source code, extract semantic anchors (`# @contract: M-*`), and verify that function/class calls precisely match the topology defined in the contract.

---

## 🛠️ Installation

This framework uses `uv` for fast, reproducible Python environment management.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/VS-212/contract-coding-framework.git
   cd contract-coding-framework
   ```

2. **Install dependencies and setup environment:**
   ```bash
   uv sync
   ```

---

## 🚀 Command-Line Interface (CLI)

The CLI is registered as `contract-coder` under `pyproject.toml`. You can run it via `uv run`:

```bash
# Display help
uv run contract-coder --help
```

### 1. Validate Autonomy Gate
Checks if a Language Contract is ready to be handled by autonomous agents (i.e., has a strict tech stack, verification plans, and no cycles).
```bash
uv run contract-coder check-autonomy api.contract.yaml
```

### 2. Visualize Architecture (Mermaid Chart)
Generates a Mermaid.js diagram of the execution graph directly to the console or to an output file.
```bash
# Output to console
uv run contract-coder visualize api.contract.yaml

# Save to file
uv run contract-coder visualize api.contract.yaml -o architecture.mermaid
```

### 3. Run Structural Alignment Audit $E(\mathcal{C})$
Audits a source directory against a Language Contract. Uses `tree-sitter` AST parsing to verify that actual call dependencies conform to the topology.
```bash
uv run contract-coder audit benchmarks/live_subagent/contract.yaml benchmarks/live_subagent/src/
```

---

## 📊 Greenfield-5 Benchmark

The **Greenfield-5** benchmark measures an AI agent's (or generated codebase's) **Structural Integrity** across 5 distinct architectural layouts of increasing complexity:

1. **SimpleAPI (Perfect)**: A controller calling a service (100% score).
2. **MissingEdge (Failure)**: A controller forgetting to call its dependent service (0% score).
3. **ForbiddenEdge (Failure)**: Circular dependencies / unintended API leakages (0% score).
4. **Independent (Perfect)**: Isolated modules with no defined topology edges (100% score).
5. **Triangle (Perfect)**: Transitive module calls aligning with the graph (100% score).

### Running the Benchmark
To execute the benchmark and print structural integrity scores:
```bash
uv run python run_benchmark.py
```

---

## 🧪 Running Unit Tests

The test suite validates contract parsing, schema validation, and graph sorting logic.
```bash
uv run pytest
```

---

## 📄 References & Papers
- [Context Engineering: A Structured Symbolic Paradigm for Agentic Systems](https://arxiv.org/abs/2604.13100)
- [GRACE: Global Reliability & Architectural Consistency Engine](https://arxiv.org/abs/2605.25665)
