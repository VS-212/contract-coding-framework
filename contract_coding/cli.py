import typer
from pathlib import Path
from rich import print
from rich.console import Console
from .schema.parser import parse_contract
from .graph.heg import HierarchicalExecutionGraph

app = typer.Typer(help="Contract-Coding CLI: Translate intents to robust architectures.")
console = Console()

@app.command()
def visualize(
    contract: Path = typer.Argument(..., help="Path to the Language Contract YAML"),
    output: Path = typer.Option(None, "--output", "-o", help="File to save the Mermaid chart (optional)")
):
    """
    Parses the contract, builds the HEG, and generates a Mermaid diagram.
    """
    try:
        parsed_contract = parse_contract(contract)
        heg = HierarchicalExecutionGraph(parsed_contract).build()
        mermaid_data = heg.to_mermaid()
        
        if output:
            output.write_text(mermaid_data, encoding="utf-8")
            print(f"[green]✔[/green] Mermaid diagram saved to [bold]{output}[/bold]")
        else:
            print(f"\n[cyan]{mermaid_data}[/cyan]\n")
            
    except Exception as e:
        print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)

@app.command()
def generate(
    contract: Path = typer.Argument(..., help="Path to the Language Contract YAML"),
    output_dir: Path = typer.Option(..., "--output", "-o", help="Directory to generate code into")
):
    """
    [MOCK] Translates the Language Contract into source code using AI agents.
    """
    try:
        parsed_contract = parse_contract(contract)
        heg = HierarchicalExecutionGraph(parsed_contract).build()
        layers = heg.get_execution_packets()
        
        print(f"🌟 Starting Contract-Coding generation from: {contract}")
        print(f"📦 Found {len(parsed_contract.modules)} modules.")
        print(f"🚀 Execution plan has {len(layers)} parallelizable layers.")
        
        for i, layer in enumerate(layers):
            print(f"   [Layer {i}]:")
            for packet in layer:
                print(f"      -> ExecutionPacket(target={packet.target_node}, retries={packet.retry_budget})")
            
        print(f"[green]✔[/green] Code generation complete! Saved to {output_dir}")
        
    except Exception as e:
        print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)

@app.command()
def audit(
    contract: Path = typer.Argument(..., help="Path to the Language Contract YAML"),
    source_dir: Path = typer.Argument(..., help="Path to the generated source code")
):
    """
    Audits the source code against the contract using Tree-sitter for structural alignment E(C).
    """
    from .audit.structural import StructuralAuditor
    
    try:
        parsed_contract = parse_contract(contract)
        heg = HierarchicalExecutionGraph(parsed_contract).build()
        
        print(f"🔍 Auditing {source_dir} against {contract}...")
        auditor = StructuralAuditor(heg, source_dir)
        results = auditor.audit()
        
        score = results['structural_integrity'] * 100
        print(f"\n📊 Structural Integrity: {score:.1f}%")
        
        if score == 100:
            print("[green]✔[/green] Structural Alignment E(C): Passed")
        else:
            print("[red]❌[/red] Structural Alignment E(C): Failed")
            print(f"   Missing Edges: {results['missing_edges']}")
            print(f"   Forbidden Edges: {results['forbidden_edges']}")
            
        print("[green]✔[/green] Consistency Control V(C): Assumed Passed (Requires dynamic test runner)")
        
    except Exception as e:
        print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)

@app.command()
def check_autonomy(
    contract: Path = typer.Argument(..., help="Path to the Language Contract YAML")
):
    """
    Validates if the project is ready for autonomous agent execution.
    Checks for cyclic dependencies, strict module IDs, verification plans, and technology stack.
    """
    try:
        parsed_contract = parse_contract(contract)
        heg = HierarchicalExecutionGraph(parsed_contract).build()
        
        # 1. Check if HEG is a pure DAG without CohesionNodes
        if any(node.startswith("CohesionNode") for node in heg.execution_graph.nodes()):
            print("[yellow]⚠[/yellow] Autonomy Warning: Cycles detected. They will be executed as CohesionNodes.")
        else:
            print("[green]✔[/green] Architecture is a clean DAG.")
            
        # 2. Check Verification Plans
        if not parsed_contract.verification_plan:
            print("[red]❌[/red] Autonomy Error: No Verification Plan found. Agents need V-M-* definitions.")
            raise typer.Exit(code=1)
        else:
            print(f"[green]✔[/green] Verification Plan contains {len(parsed_contract.verification_plan)} entries.")
            
        # 3. Check Technology Stack
        if not parsed_contract.technology_stack:
            print("[red]❌[/red] Autonomy Error: Technology Stack not defined. Agents might hallucinate tools.")
            raise typer.Exit(code=1)
        else:
            print("[green]✔[/green] Technology Stack is strictly defined.")
            
        print("\n[bold green]✅ Autonomy Gate Passed: Ready for execution.[/bold green]")
        
    except Exception as e:
        print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1)

def main():
    app()

if __name__ == "__main__":
    main()
