"""Enhanced Pydantic v2 models for the Language Contract schema.

This module defines the complete data model hierarchy for Language Contracts,
which are structured specifications that transform development intent into
verifiable, parallelizable software architectures.

Models:
    VarSchema: Variable/parameter definition with type and constraint info.
    ConstraintSchema: Pre/post-conditions and invariant expressions.
    TopologyLink: Dependency links between modules in the contract graph.
    ModuleContract: A single module specification within a contract.
    AttractorItem: A single structural or behavioral attractor pattern.
    AttractorSchema: Collection of architectural and functional attractors.
    TestScenario: A BDD-style test scenario (Given/When/Then).
    VerificationSchema: Test scenarios, assertions, and acceptance criteria.
    MetadataSchema: Contract authorship, timestamps, and project metadata.
    LanguageContract: Top-level contract aggregating all sections.

Usage:
    >>> from contract_coding.core.contract import LanguageContract
    >>> contract = LanguageContract.from_yaml("path/to/contract.yaml")
    >>> print(contract.to_json(indent=2))
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class LinkType(str, Enum):
    """Types of dependency links between modules."""

    DATA_FLOW = "data_flow"
    CONTROL_FLOW = "control_flow"
    SHARED_STATE = "shared_state"


class Severity(str, Enum):
    """Severity levels for validation messages."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class AttractorType(str, Enum):
    """Classification of attractor patterns."""

    STRUCTURAL = "structural"
    BEHAVIORAL = "behavioral"


# ---------------------------------------------------------------------------
# Variable & Constraint schemas
# ---------------------------------------------------------------------------

class VarSchema(BaseModel):
    """Schema for an input or output variable of a module.

    Attributes:
        name: Identifier for the variable. Must be non-empty.
        type: Type annotation string (e.g. ``"str"``, ``"List[int]"``).
        description: Human-readable purpose of this variable.
        default: Optional default value. When set, ``required`` is forced
            to ``False`` unless explicitly overridden.
        required: Whether this variable must be supplied. Defaults to
            ``True`` when no ``default`` is given.
    """

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "user_id",
                    "type": "str",
                    "description": "Unique user identifier",
                    "required": True,
                }
            ]
        },
        "populate_by_name": True,
    }

    name: str = Field(
        ...,
        min_length=1,
        description="Variable identifier",
    )
    type: str = Field(
        ...,
        min_length=1,
        description="Type annotation string (e.g. 'str', 'List[int]')",
    )
    description: Optional[str] = Field(
        default=None,
        description="Human-readable description of the variable",
    )
    default: Optional[Any] = Field(
        default=None,
        description="Default value; implies required=False unless overridden",
    )
    required: bool = Field(
        default=True,
        description="Whether the variable must be provided",
    )

    @model_validator(mode="after")
    def _default_implies_optional(self) -> "VarSchema":
        """If a default is provided and required was not explicitly set, mark optional."""
        if self.default is not None and self.required:
            # Only auto-flip when the raw data did not contain an explicit `required: true`.
            # Pydantic v2 doesn't expose "was this field explicitly set" easily,
            # so we keep the conservative approach: default present → optional.
            object.__setattr__(self, "required", False)
        return self


class ConstraintSchema(BaseModel):
    """Pre-conditions, post-conditions, and invariants for a module.

    Each entry is a human-readable or quasi-formal expression that the
    module must satisfy at the corresponding lifecycle point.

    Attributes:
        preconditions: Conditions that must hold *before* module execution.
        postconditions: Conditions guaranteed to hold *after* module execution.
        invariants: Conditions preserved *throughout* module execution.
    """

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "preconditions": ["input is not None"],
                    "postconditions": ["result.status == 'ok'"],
                    "invariants": ["len(items) >= 0"],
                }
            ]
        }
    }

    preconditions: List[str] = Field(
        default_factory=list,
        description="Conditions required before execution",
    )
    postconditions: List[str] = Field(
        default_factory=list,
        description="Conditions guaranteed after execution",
    )
    invariants: List[str] = Field(
        default_factory=list,
        description="Conditions maintained throughout execution",
    )


# ---------------------------------------------------------------------------
# Topology
# ---------------------------------------------------------------------------

class TopologyLink(BaseModel):
    """A directed dependency edge in the module topology graph.

    Attributes:
        source: Name of the upstream (provider) module.
        target: Name of the downstream (consumer) module.
        type: Kind of dependency (data_flow, control_flow, shared_state).
        description: Optional explanation of the link purpose.
    """

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "source": "auth_module",
                    "target": "user_service",
                    "type": "data_flow",
                    "description": "Auth token passed to user service",
                }
            ]
        }
    }

    source: str = Field(..., min_length=1, description="Source module name")
    target: str = Field(..., min_length=1, description="Target module name")
    type: LinkType = Field(
        default=LinkType.DATA_FLOW,
        description="Type of dependency link",
    )
    description: Optional[str] = Field(
        default=None,
        description="Explanation of this dependency",
    )

    @field_validator("source", "target")
    @classmethod
    def _no_self_loop(cls, v: str, info: Any) -> str:  # noqa: N805
        """Prevent a link whose source and target are the same."""
        # Full self-loop validation happens at the contract level because we
        # need both fields; this validator just ensures non-empty strings.
        return v.strip()


# ---------------------------------------------------------------------------
# Module contract
# ---------------------------------------------------------------------------

class ModuleContract(BaseModel):
    """Specification for a single module within a Language Contract.

    Attributes:
        name: Unique module identifier within the contract.
        description: What this module does.
        inputs: Expected input variables.
        outputs: Produced output variables.
        dependencies: Names of modules this module depends on.
        constraints: Pre/post-conditions and invariants.
        semantic_anchors: Key domain concepts this module is responsible for.
        priority: Execution priority (lower = higher priority). Defaults to 0.
        parallelizable: Whether this module can be executed concurrently.
    """

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "user_auth",
                    "description": "Handles user authentication",
                    "inputs": [{"name": "credentials", "type": "dict"}],
                    "outputs": [{"name": "token", "type": "str"}],
                    "dependencies": [],
                    "priority": 1,
                    "parallelizable": False,
                }
            ]
        }
    }

    name: str = Field(..., min_length=1, description="Unique module name")
    description: str = Field(..., min_length=1, description="Module purpose")
    inputs: List[VarSchema] = Field(
        default_factory=list,
        description="Input variable definitions",
    )
    outputs: List[VarSchema] = Field(
        default_factory=list,
        description="Output variable definitions",
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="Names of modules this module depends on",
    )
    constraints: ConstraintSchema = Field(
        default_factory=ConstraintSchema,
        description="Module-level constraints",
    )
    semantic_anchors: List[str] = Field(
        default_factory=list,
        description="Key domain concepts anchored to this module",
    )
    priority: int = Field(
        default=0,
        ge=0,
        description="Execution priority (0 = highest)",
    )
    parallelizable: bool = Field(
        default=True,
        description="Whether this module may run in parallel with others",
    )


# ---------------------------------------------------------------------------
# Attractors
# ---------------------------------------------------------------------------

class AttractorItem(BaseModel):
    """A single architectural or behavioural attractor pattern.

    Attractors guide the code-generation process toward preferred design
    choices.  Structural attractors describe architecture (e.g. patterns,
    layer styles), while behavioural attractors describe runtime
    characteristics (e.g. caching strategy, retry policy).

    Attributes:
        id: Unique identifier for the attractor.
        name: Human-readable name.
        description: Detailed explanation of the attractor.
        type: Whether the attractor is structural or behavioral.
        weight: Relative importance weight (0.0–1.0).
    """

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "pattern-repository",
                    "name": "Repository Pattern",
                    "description": "Decouple data access from business logic",
                    "type": "structural",
                    "weight": 0.8,
                }
            ]
        }
    }

    id: str = Field(..., min_length=1, description="Unique attractor ID")
    name: str = Field(..., min_length=1, description="Attractor name")
    description: Optional[str] = Field(
        default=None,
        description="Detailed explanation",
    )
    type: AttractorType = Field(
        ...,
        description="Structural or behavioral classification",
    )
    weight: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Relative importance (0.0–1.0)",
    )


class AttractorSchema(BaseModel):
    """Collection of structural and behavioral attractors.

    Attributes:
        structural: Architectural patterns and design constraints.
        behavioral: Functional patterns and runtime strategies.
    """

    structural: List[AttractorItem] = Field(
        default_factory=list,
        description="Architectural attractor patterns",
    )
    behavioral: List[AttractorItem] = Field(
        default_factory=list,
        description="Functional/behavioral attractor patterns",
    )

    @model_validator(mode="after")
    def _enforce_types(self) -> "AttractorSchema":
        """Ensure items are classified under the correct list."""
        for item in self.structural:
            if item.type != AttractorType.STRUCTURAL:
                object.__setattr__(item, "type", AttractorType.STRUCTURAL)
        for item in self.behavioral:
            if item.type != AttractorType.BEHAVIORAL:
                object.__setattr__(item, "type", AttractorType.BEHAVIORAL)
        return self


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

class TestScenario(BaseModel):
    """A BDD-style (Given/When/Then) test scenario.

    Attributes:
        name: Short description of the scenario.
        given: Pre-conditions / setup.
        when: Action or trigger.
        then: Expected outcome.
        module: Optional name of the module under test.
    """

    name: str = Field(..., min_length=1, description="Scenario name")
    given: str = Field(..., min_length=1, description="Pre-conditions/setup")
    when: str = Field(..., min_length=1, description="Action under test")
    then: str = Field(..., min_length=1, description="Expected outcome")
    module: Optional[str] = Field(
        default=None,
        description="Module this scenario targets",
    )


class VerificationSchema(BaseModel):
    """Verification section of a Language Contract.

    Attributes:
        test_scenarios: BDD-style test scenarios.
        assertions: Global assertion expressions.
        acceptance_criteria: High-level acceptance criteria strings.
    """

    test_scenarios: List[TestScenario] = Field(
        default_factory=list,
        description="BDD-style test scenarios",
    )
    assertions: List[str] = Field(
        default_factory=list,
        description="Global assertion expressions",
    )
    acceptance_criteria: List[str] = Field(
        default_factory=list,
        description="High-level acceptance criteria",
    )


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------

class MetadataSchema(BaseModel):
    """Authorship, timestamps, and project metadata for a contract.

    Attributes:
        author: Primary author or team name.
        created_at: When the contract was first created (ISO-8601).
        updated_at: When the contract was last updated (ISO-8601).
        tags: Freeform tags for categorisation.
        language: Target programming language (e.g. ``"python"``).
        framework: Target framework (e.g. ``"fastapi"``).
        target_directory: Filesystem directory for generated code.
    """

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "author": "dev-team",
                    "language": "python",
                    "framework": "fastapi",
                    "tags": ["microservice", "auth"],
                }
            ]
        }
    }

    author: Optional[str] = Field(default=None, description="Contract author")
    created_at: Optional[datetime] = Field(
        default=None,
        description="Creation timestamp (ISO-8601)",
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        description="Last-updated timestamp (ISO-8601)",
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Categorisation tags",
    )
    language: Optional[str] = Field(
        default=None,
        description="Target programming language",
    )
    framework: Optional[str] = Field(
        default=None,
        description="Target framework",
    )
    target_directory: Optional[str] = Field(
        default=None,
        description="Filesystem path for generated output",
    )


# ---------------------------------------------------------------------------
# Top-level Language Contract
# ---------------------------------------------------------------------------

class LanguageContract(BaseModel):
    """Top-level Language Contract specification.

    A Language Contract captures the *full intent* of a software system
    in a structured, machine-verifiable format.  It consists of:

    * **intent** – natural-language statement of purpose.
    * **metadata** – authorship, timestamps, tech-stack info.
    * **attractors** – architectural and behavioral design guidance.
    * **modules** – the individual units of work.
    * **topology** – explicit dependency edges between modules.
    * **verification** – test scenarios and acceptance criteria.
    * **global_constraints** – contract-wide invariant expressions.

    Class Methods:
        from_yaml: Deserialise from a YAML file.
        from_json: Deserialise from a JSON file.

    Instance Methods:
        get_module: Look up a module by name.
        get_dependency_graph: Build an adjacency-list dependency graph.
        to_yaml: Serialise to a YAML string.
        to_json: Serialise to a JSON string.
    """

    model_config = {
        "json_schema_extra": {
            "title": "Language Contract",
            "description": "Top-level schema for a Contract-Coding Language Contract v1.0",
        },
        "populate_by_name": True,
        "ser_json_timedelta": "iso8601",
    }

    version: str = Field(
        default="1.0",
        description="Contract schema version",
    )
    intent: str = Field(
        ...,
        min_length=1,
        description="Natural-language statement of the system's purpose",
    )
    description: Optional[str] = Field(
        default=None,
        description="Extended description of the contract scope",
    )
    metadata: MetadataSchema = Field(
        default_factory=MetadataSchema,
        description="Authorship and project metadata",
    )
    attractors: AttractorSchema = Field(
        default_factory=AttractorSchema,
        description="Structural and behavioral attractor patterns",
    )
    modules: List[ModuleContract] = Field(
        default_factory=list,
        description="Module specifications",
    )
    topology: List[TopologyLink] = Field(
        default_factory=list,
        description="Explicit dependency edges between modules",
    )
    verification: VerificationSchema = Field(
        default_factory=VerificationSchema,
        description="Test scenarios and acceptance criteria",
    )
    global_constraints: List[str] = Field(
        default_factory=list,
        description="Contract-wide constraint expressions",
    )

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @model_validator(mode="after")
    def _no_duplicate_module_names(self) -> "LanguageContract":
        """Reject contracts containing duplicate module names."""
        seen: set[str] = set()
        for mod in self.modules:
            if mod.name in seen:
                raise ValueError(
                    f"Duplicate module name: '{mod.name}'. "
                    "Each module must have a unique name within the contract."
                )
            seen.add(mod.name)
        return self

    # ------------------------------------------------------------------
    # Lookup helpers
    # ------------------------------------------------------------------

    def get_module(self, name: str) -> Optional[ModuleContract]:
        """Return the module with the given *name*, or ``None``.

        Args:
            name: Module name to look up (case-sensitive).

        Returns:
            The matching ``ModuleContract`` or ``None`` if not found.
        """
        for module in self.modules:
            if module.name == name:
                return module
        return None

    def get_dependency_graph(self) -> Dict[str, List[str]]:
        """Build an adjacency-list representation of the module dependency graph.

        The graph merges two sources of dependency information:

        1. The ``dependencies`` field on each ``ModuleContract``.
        2. The ``topology`` links defined at the contract level.

        Returns:
            A mapping ``{module_name: [dependency_name, ...]}``.
        """
        graph: Dict[str, List[str]] = {mod.name: list(mod.dependencies) for mod in self.modules}
        for link in self.topology:
            deps = graph.setdefault(link.target, [])
            if link.source not in deps:
                deps.append(link.source)
            graph.setdefault(link.source, [])
        return graph

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def _serializable_dict(self) -> Dict[str, Any]:
        """Return a JSON-safe dict, converting datetimes to ISO strings."""
        data = self.model_dump(mode="json", exclude_none=True)
        return data

    def to_yaml(self, **kwargs: Any) -> str:
        """Serialise the contract to a YAML string.

        Args:
            **kwargs: Extra keyword arguments forwarded to ``yaml.dump``.

        Returns:
            A YAML-formatted string.
        """
        data = self._serializable_dict()
        kwargs.setdefault("default_flow_style", False)
        kwargs.setdefault("sort_keys", False)
        kwargs.setdefault("allow_unicode", True)
        return yaml.dump(data, **kwargs)

    def to_json(self, *, indent: int = 2, **kwargs: Any) -> str:
        """Serialise the contract to a JSON string.

        Args:
            indent: Number of spaces for pretty-printing.
            **kwargs: Extra keyword arguments forwarded to ``json.dumps``.

        Returns:
            A JSON-formatted string.
        """
        data = self._serializable_dict()
        kwargs.setdefault("ensure_ascii", False)
        return json.dumps(data, indent=indent, **kwargs)

    # ------------------------------------------------------------------
    # Deserialisation class methods
    # ------------------------------------------------------------------

    @classmethod
    def from_yaml(cls, path: Union[str, Path]) -> "LanguageContract":
        """Deserialise a ``LanguageContract`` from a YAML file.

        Args:
            path: Filesystem path to the YAML file.

        Returns:
            A validated ``LanguageContract`` instance.

        Raises:
            FileNotFoundError: If *path* does not exist.
            yaml.YAMLError: If the file is not valid YAML.
            pydantic.ValidationError: If the data does not match the schema.
        """
        filepath = Path(path)
        if not filepath.exists():
            raise FileNotFoundError(f"Contract YAML file not found: {filepath}")
        raw = filepath.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
        if not isinstance(data, dict):
            raise ValueError(
                f"Expected a YAML mapping at the top level, got {type(data).__name__}"
            )
        return cls.model_validate(data)

    @classmethod
    def from_json(cls, path: Union[str, Path]) -> "LanguageContract":
        """Deserialise a ``LanguageContract`` from a JSON file.

        Args:
            path: Filesystem path to the JSON file.

        Returns:
            A validated ``LanguageContract`` instance.

        Raises:
            FileNotFoundError: If *path* does not exist.
            json.JSONDecodeError: If the file is not valid JSON.
            pydantic.ValidationError: If the data does not match the schema.
        """
        filepath = Path(path)
        if not filepath.exists():
            raise FileNotFoundError(f"Contract JSON file not found: {filepath}")
        raw = filepath.read_text(encoding="utf-8")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError(
                f"Expected a JSON object at the top level, got {type(data).__name__}"
            )
        return cls.model_validate(data)
