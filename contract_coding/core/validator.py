"""Contract validator for semantic, structural, and consistency checks.

This module provides ``ContractValidator``, which performs deep
validation of a ``LanguageContract`` beyond what Pydantic's type system
can express.  Checks include:

* **Completeness** – every module has at least one input or output,
  a non-empty description, etc.
* **Consistency** – no duplicate module names, all dependency references
  point to existing modules, topology links reference existing modules.
* **Dependencies** – no circular dependencies in the module graph.
* **Verification** – test scenarios referencing a module match an actual
  module name; assertions are syntactically non-empty.

Classes:
    Severity: Enum of ERROR / WARNING / INFO.
    ValidationMessage: A single validation finding.
    ValidationResult: Aggregated validation outcome.
    ContractValidator: Entry point for running all validation checks.

Usage:
    >>> from contract_coding.core.validator import ContractValidator
    >>> result = ContractValidator().validate(contract)
    >>> if not result.is_valid:
    ...     for err in result.errors:
    ...         print(err)
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field

from contract_coding.core.contract import LanguageContract


# ---------------------------------------------------------------------------
# Severity enum
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    """Severity level for validation messages."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


# ---------------------------------------------------------------------------
# Validation message models
# ---------------------------------------------------------------------------

class ValidationMessage(BaseModel):
    """A single validation finding.

    Attributes:
        field: Dot-separated path to the offending field (e.g.
            ``"modules.0.name"``).
        message: Human-readable description of the issue.
        severity: ``ERROR``, ``WARNING``, or ``INFO``.
        suggestion: Optional actionable fix suggestion.
    """

    field: str = Field(..., description="Dot-path to the offending field")
    message: str = Field(..., description="Description of the issue")
    severity: Severity = Field(default=Severity.ERROR, description="Issue severity")
    suggestion: Optional[str] = Field(
        default=None,
        description="Actionable fix suggestion",
    )

    def __str__(self) -> str:
        prefix = self.severity.value.upper()
        text = f"[{prefix}] {self.field}: {self.message}"
        if self.suggestion:
            text += f" (suggestion: {self.suggestion})"
        return text


# Convenience aliases used in public API docs.
ValidationError = ValidationMessage
"""Alias – a ``ValidationMessage`` with ``severity=ERROR``."""

ValidationWarning = ValidationMessage
"""Alias – a ``ValidationMessage`` with ``severity=WARNING``."""


# ---------------------------------------------------------------------------
# Validation result
# ---------------------------------------------------------------------------

class ValidationResult(BaseModel):
    """Aggregated result of validating a ``LanguageContract``.

    Attributes:
        is_valid: ``True`` when there are **no** ERROR-level messages.
        errors: Messages with ``severity=ERROR``.
        warnings: Messages with ``severity=WARNING``.
        suggestions: Messages with ``severity=INFO``.
    """

    is_valid: bool = Field(default=True, description="True when no errors exist")
    errors: List[ValidationMessage] = Field(
        default_factory=list,
        description="ERROR-level findings",
    )
    warnings: List[ValidationMessage] = Field(
        default_factory=list,
        description="WARNING-level findings",
    )
    suggestions: List[ValidationMessage] = Field(
        default_factory=list,
        description="INFO-level suggestions",
    )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _add(self, msg: ValidationMessage) -> None:
        """Route a message to the correct list and update ``is_valid``."""
        if msg.severity is Severity.ERROR:
            self.errors.append(msg)
            self.is_valid = False
        elif msg.severity is Severity.WARNING:
            self.warnings.append(msg)
        else:
            self.suggestions.append(msg)

    @property
    def all_messages(self) -> List[ValidationMessage]:
        """Return all messages regardless of severity."""
        return self.errors + self.warnings + self.suggestions

    def summary(self) -> str:
        """Return a one-line summary of the validation result.

        Returns:
            A string like ``"2 errors, 1 warning, 0 info"`` or
            ``"Valid (0 errors, 0 warnings, 0 info)"``.
        """
        e, w, i = len(self.errors), len(self.warnings), len(self.suggestions)
        status = "Valid" if self.is_valid else "Invalid"
        return f"{status} ({e} error(s), {w} warning(s), {i} info)"


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

class ContractValidator:
    """Validates a ``LanguageContract`` for completeness, consistency, and correctness.

    All checks are deterministic and side-effect-free.  The validator
    never mutates the contract.

    Example::

        validator = ContractValidator()
        result = validator.validate(contract)
        print(result.summary())
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(self, contract: LanguageContract) -> ValidationResult:
        """Run **all** validation checks on *contract*.

        This is the recommended entry point.  It calls
        ``validate_completeness``, ``validate_consistency``, and
        ``validate_dependencies`` in sequence, merging their results.

        Args:
            contract: The contract to validate.

        Returns:
            A ``ValidationResult`` aggregating all findings.
        """
        result = ValidationResult()
        self._run_completeness(contract, result)
        self._run_consistency(contract, result)
        self._run_dependencies(contract, result)
        self._run_verification(contract, result)
        return result

    def validate_completeness(self, contract: LanguageContract) -> ValidationResult:
        """Check that the contract is *complete* (no missing critical data).

        Args:
            contract: The contract to validate.

        Returns:
            A ``ValidationResult`` with completeness findings.
        """
        result = ValidationResult()
        self._run_completeness(contract, result)
        return result

    def validate_consistency(self, contract: LanguageContract) -> ValidationResult:
        """Check that the contract is internally *consistent*.

        Args:
            contract: The contract to validate.

        Returns:
            A ``ValidationResult`` with consistency findings.
        """
        result = ValidationResult()
        self._run_consistency(contract, result)
        return result

    def validate_dependencies(self, contract: LanguageContract) -> ValidationResult:
        """Check dependency validity (references, cycles).

        Args:
            contract: The contract to validate.

        Returns:
            A ``ValidationResult`` with dependency findings.
        """
        result = ValidationResult()
        self._run_dependencies(contract, result)
        return result

    # ------------------------------------------------------------------
    # Completeness checks
    # ------------------------------------------------------------------

    def _run_completeness(
        self,
        contract: LanguageContract,
        result: ValidationResult,
    ) -> None:
        """Populate *result* with completeness findings."""
        # Contract-level
        if not contract.modules:
            result._add(ValidationMessage(
                field="modules",
                message="Contract has no modules defined",
                severity=Severity.WARNING,
                suggestion="Add at least one module to make the contract actionable.",
            ))

        if not contract.intent.strip():
            result._add(ValidationMessage(
                field="intent",
                message="Intent is blank",
                severity=Severity.ERROR,
                suggestion="Provide a clear statement of the system's purpose.",
            ))

        if contract.metadata.author is None:
            result._add(ValidationMessage(
                field="metadata.author",
                message="No author specified",
                severity=Severity.INFO,
                suggestion="Set metadata.author for traceability.",
            ))

        if contract.metadata.language is None:
            result._add(ValidationMessage(
                field="metadata.language",
                message="No target language specified",
                severity=Severity.INFO,
                suggestion="Set metadata.language (e.g. 'python') to guide code generation.",
            ))

        # Module-level
        for idx, mod in enumerate(contract.modules):
            prefix = f"modules.{idx} ({mod.name})"

            if not mod.inputs and not mod.outputs:
                result._add(ValidationMessage(
                    field=f"{prefix}",
                    message="Module has no inputs and no outputs",
                    severity=Severity.WARNING,
                    suggestion="Define at least one input or output.",
                ))

            if not mod.semantic_anchors:
                result._add(ValidationMessage(
                    field=f"{prefix}.semantic_anchors",
                    message="No semantic anchors defined",
                    severity=Severity.INFO,
                    suggestion="Add semantic anchors for better traceability.",
                ))

            # Constraint quality hints
            c = mod.constraints
            if not c.preconditions and not c.postconditions and not c.invariants:
                result._add(ValidationMessage(
                    field=f"{prefix}.constraints",
                    message="No constraints defined for this module",
                    severity=Severity.INFO,
                    suggestion="Add preconditions, postconditions, or invariants.",
                ))

        # Verification
        if not contract.verification.test_scenarios:
            result._add(ValidationMessage(
                field="verification.test_scenarios",
                message="No test scenarios defined",
                severity=Severity.WARNING,
                suggestion="Add at least one test scenario for verifiability.",
            ))

        if not contract.verification.acceptance_criteria:
            result._add(ValidationMessage(
                field="verification.acceptance_criteria",
                message="No acceptance criteria defined",
                severity=Severity.INFO,
                suggestion="Add acceptance criteria for clearer done-definition.",
            ))

    # ------------------------------------------------------------------
    # Consistency checks
    # ------------------------------------------------------------------

    def _run_consistency(
        self,
        contract: LanguageContract,
        result: ValidationResult,
    ) -> None:
        """Populate *result* with consistency findings."""
        module_names: Set[str] = set()

        # Duplicate module names (also caught by Pydantic, but we give
        # a clearer message here at the WARNING level).
        seen: dict[str, int] = {}
        for idx, mod in enumerate(contract.modules):
            if mod.name in seen:
                result._add(ValidationMessage(
                    field=f"modules.{idx}.name",
                    message=(
                        f"Duplicate module name '{mod.name}' "
                        f"(first seen at modules.{seen[mod.name]})"
                    ),
                    severity=Severity.ERROR,
                    suggestion="Rename one of the duplicate modules.",
                ))
            else:
                seen[mod.name] = idx
            module_names.add(mod.name)

        # Topology links reference existing modules
        for idx, link in enumerate(contract.topology):
            if link.source not in module_names:
                result._add(ValidationMessage(
                    field=f"topology.{idx}.source",
                    message=f"Topology source '{link.source}' is not a defined module",
                    severity=Severity.ERROR,
                    suggestion=f"Add a module named '{link.source}' or fix the reference.",
                ))
            if link.target not in module_names:
                result._add(ValidationMessage(
                    field=f"topology.{idx}.target",
                    message=f"Topology target '{link.target}' is not a defined module",
                    severity=Severity.ERROR,
                    suggestion=f"Add a module named '{link.target}' or fix the reference.",
                ))
            if link.source == link.target:
                result._add(ValidationMessage(
                    field=f"topology.{idx}",
                    message=f"Self-referencing topology link on '{link.source}'",
                    severity=Severity.WARNING,
                    suggestion="Remove the self-loop or split into separate modules.",
                ))

        # Module dependencies reference existing modules
        for idx, mod in enumerate(contract.modules):
            for dep in mod.dependencies:
                if dep not in module_names:
                    result._add(ValidationMessage(
                        field=f"modules.{idx} ({mod.name}).dependencies",
                        message=f"Dependency '{dep}' is not a defined module",
                        severity=Severity.ERROR,
                        suggestion=f"Add a module named '{dep}' or remove the dependency.",
                    ))
                if dep == mod.name:
                    result._add(ValidationMessage(
                        field=f"modules.{idx} ({mod.name}).dependencies",
                        message=f"Module '{mod.name}' lists itself as a dependency",
                        severity=Severity.ERROR,
                        suggestion="Remove the self-dependency.",
                    ))

        # Variable type validation (basic heuristic)
        _KNOWN_TYPES = {
            "str", "string", "int", "integer", "float", "number",
            "bool", "boolean", "list", "dict", "any", "none",
            "bytes", "datetime", "date", "time", "uuid",
            "optional", "union", "tuple", "set", "frozenset",
        }

        for idx, mod in enumerate(contract.modules):
            for var_list_name in ("inputs", "outputs"):
                var_list = getattr(mod, var_list_name)
                for vidx, var in enumerate(var_list):
                    # Extract base type (before '[' for generics)
                    base = var.type.split("[")[0].strip().lower()
                    if base not in _KNOWN_TYPES:
                        result._add(ValidationMessage(
                            field=f"modules.{idx} ({mod.name}).{var_list_name}.{vidx}.type",
                            message=f"Type '{var.type}' is not a commonly recognised type",
                            severity=Severity.INFO,
                            suggestion=(
                                "Verify the type annotation is correct. "
                                "Common types: str, int, float, bool, list, dict, Optional[T]."
                            ),
                        ))

        # Constraint expression validation (non-empty strings)
        for idx, mod in enumerate(contract.modules):
            prefix = f"modules.{idx} ({mod.name}).constraints"
            for list_name in ("preconditions", "postconditions", "invariants"):
                entries: list[str] = getattr(mod.constraints, list_name)
                for eidx, expr in enumerate(entries):
                    if not expr.strip():
                        result._add(ValidationMessage(
                            field=f"{prefix}.{list_name}.{eidx}",
                            message="Empty constraint expression",
                            severity=Severity.ERROR,
                            suggestion="Remove or replace with a meaningful expression.",
                        ))

        # Global constraint validation
        for cidx, expr in enumerate(contract.global_constraints):
            if not expr.strip():
                result._add(ValidationMessage(
                    field=f"global_constraints.{cidx}",
                    message="Empty global constraint expression",
                    severity=Severity.ERROR,
                    suggestion="Remove or replace with a meaningful expression.",
                ))

    # ------------------------------------------------------------------
    # Dependency graph checks
    # ------------------------------------------------------------------

    def _run_dependencies(
        self,
        contract: LanguageContract,
        result: ValidationResult,
    ) -> None:
        """Check for circular dependencies in the module graph."""
        graph = contract.get_dependency_graph()
        cycles = self._find_cycles(graph)
        for cycle in cycles:
            cycle_str = " → ".join(cycle + [cycle[0]])
            result._add(ValidationMessage(
                field="topology / dependencies",
                message=f"Circular dependency detected: {cycle_str}",
                severity=Severity.ERROR,
                suggestion=(
                    "Break the cycle by introducing an interface, event bus, "
                    "or restructuring module boundaries."
                ),
            ))

    @staticmethod
    def _find_cycles(graph: Dict[str, list[str]]) -> list[list[str]]:
        """Find all elementary cycles in a directed graph using DFS.

        Args:
            graph: Adjacency-list ``{node: [neighbour, ...]}``.

        Returns:
            A list of cycles, each cycle being a list of node names.
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = {node: WHITE for node in graph}
        parent: Dict[str, Optional[str]] = {node: None for node in graph}
        cycles: list[list[str]] = []
        found_cycles: set[tuple[str, ...]] = set()

        def _dfs(node: str) -> None:
            color[node] = GRAY
            for neighbour in graph.get(node, []):
                if neighbour not in color:
                    # Node referenced but not in graph keys – skip
                    continue
                if color[neighbour] == GRAY:
                    # Back edge → cycle
                    cycle: list[str] = []
                    current = node
                    while current != neighbour:
                        cycle.append(current)
                        current = parent.get(current)  # type: ignore[assignment]
                        if current is None:
                            break
                    cycle.append(neighbour)
                    cycle.reverse()
                    # Normalise to avoid duplicate reports
                    canon = tuple(cycle[cycle.index(min(cycle)):] + cycle[:cycle.index(min(cycle))])
                    if canon not in found_cycles:
                        found_cycles.add(canon)
                        cycles.append(cycle)
                elif color[neighbour] == WHITE:
                    parent[neighbour] = node
                    _dfs(neighbour)
            color[node] = BLACK

        for node in graph:
            if color[node] == WHITE:
                _dfs(node)

        return cycles

    # ------------------------------------------------------------------
    # Verification checks
    # ------------------------------------------------------------------

    def _run_verification(
        self,
        contract: LanguageContract,
        result: ValidationResult,
    ) -> None:
        """Check that verification items are consistent with modules."""
        module_names = {mod.name for mod in contract.modules}

        for idx, scenario in enumerate(contract.verification.test_scenarios):
            if scenario.module and scenario.module not in module_names:
                result._add(ValidationMessage(
                    field=f"verification.test_scenarios.{idx}.module",
                    message=(
                        f"Test scenario '{scenario.name}' references module "
                        f"'{scenario.module}' which does not exist"
                    ),
                    severity=Severity.ERROR,
                    suggestion=(
                        f"Change the module reference to one of: "
                        f"{', '.join(sorted(module_names)) or '(none defined)'}."
                    ),
                ))

        # Check for empty assertion strings
        for idx, assertion in enumerate(contract.verification.assertions):
            if not assertion.strip():
                result._add(ValidationMessage(
                    field=f"verification.assertions.{idx}",
                    message="Empty assertion expression",
                    severity=Severity.ERROR,
                    suggestion="Remove or replace with a meaningful assertion.",
                ))
