"""JSON Schema definition for Language Contract v1.0.

This module provides the canonical JSON Schema dict for validating
Language Contract documents, along with utility functions for schema
retrieval and validation.

The schema is maintained as a Python data structure rather than an
external file so that it is always in sync with the Pydantic models
in ``contract_coding.core.contract``.

Functions:
    get_schema: Return the JSON Schema dict.
    get_schema_version: Return the schema version string.
    validate_against_schema: Validate arbitrary data against the schema.

Usage:
    >>> from contract_coding.core.schema import validate_against_schema
    >>> errors = validate_against_schema(my_dict)
    >>> if errors:
    ...     for e in errors:
    ...         print(e)
"""

from __future__ import annotations

from typing import Any, Dict, List

import jsonschema

# ---------------------------------------------------------------------------
# Schema version
# ---------------------------------------------------------------------------

SCHEMA_VERSION: str = "1.0"
"""Current version of the Language Contract JSON Schema."""

# ---------------------------------------------------------------------------
# JSON Schema definition
# ---------------------------------------------------------------------------

_VAR_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "description": "Variable / parameter definition.",
    "required": ["name", "type"],
    "properties": {
        "name": {
            "type": "string",
            "minLength": 1,
            "description": "Variable identifier.",
        },
        "type": {
            "type": "string",
            "minLength": 1,
            "description": "Type annotation string.",
        },
        "description": {
            "type": ["string", "null"],
            "description": "Human-readable description.",
        },
        "default": {
            "description": "Default value (any type).",
        },
        "required": {
            "type": "boolean",
            "default": True,
            "description": "Whether the variable must be provided.",
        },
    },
    "additionalProperties": False,
}

_CONSTRAINT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "description": "Pre/post-conditions and invariants.",
    "properties": {
        "preconditions": {
            "type": "array",
            "items": {"type": "string"},
            "default": [],
            "description": "Conditions that must hold before execution.",
        },
        "postconditions": {
            "type": "array",
            "items": {"type": "string"},
            "default": [],
            "description": "Conditions guaranteed after execution.",
        },
        "invariants": {
            "type": "array",
            "items": {"type": "string"},
            "default": [],
            "description": "Conditions preserved throughout execution.",
        },
    },
    "additionalProperties": False,
}

_TOPOLOGY_LINK_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "description": "Directed dependency edge between modules.",
    "required": ["source", "target"],
    "properties": {
        "source": {
            "type": "string",
            "minLength": 1,
            "description": "Source (upstream) module name.",
        },
        "target": {
            "type": "string",
            "minLength": 1,
            "description": "Target (downstream) module name.",
        },
        "type": {
            "type": "string",
            "enum": ["data_flow", "control_flow", "shared_state"],
            "default": "data_flow",
            "description": "Kind of dependency link.",
        },
        "description": {
            "type": ["string", "null"],
            "description": "Explanation of this dependency.",
        },
    },
    "additionalProperties": False,
}

_MODULE_CONTRACT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "description": "Specification for a single module.",
    "required": ["name", "description"],
    "properties": {
        "name": {
            "type": "string",
            "minLength": 1,
            "description": "Unique module name.",
        },
        "description": {
            "type": "string",
            "minLength": 1,
            "description": "Module purpose.",
        },
        "inputs": {
            "type": "array",
            "items": _VAR_SCHEMA,
            "default": [],
            "description": "Input variable definitions.",
        },
        "outputs": {
            "type": "array",
            "items": _VAR_SCHEMA,
            "default": [],
            "description": "Output variable definitions.",
        },
        "dependencies": {
            "type": "array",
            "items": {"type": "string"},
            "default": [],
            "description": "Names of modules this module depends on.",
        },
        "constraints": {
            **_CONSTRAINT_SCHEMA,
            "default": {},
        },
        "semantic_anchors": {
            "type": "array",
            "items": {"type": "string"},
            "default": [],
            "description": "Key domain concepts anchored to this module.",
        },
        "priority": {
            "type": "integer",
            "minimum": 0,
            "default": 0,
            "description": "Execution priority (0 = highest).",
        },
        "parallelizable": {
            "type": "boolean",
            "default": True,
            "description": "Whether this module may run in parallel.",
        },
    },
    "additionalProperties": False,
}

_ATTRACTOR_ITEM_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "description": "A single attractor pattern.",
    "required": ["id", "name", "type"],
    "properties": {
        "id": {
            "type": "string",
            "minLength": 1,
            "description": "Unique attractor ID.",
        },
        "name": {
            "type": "string",
            "minLength": 1,
            "description": "Attractor name.",
        },
        "description": {
            "type": ["string", "null"],
            "description": "Detailed explanation.",
        },
        "type": {
            "type": "string",
            "enum": ["structural", "behavioral"],
            "description": "Structural or behavioral classification.",
        },
        "weight": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "default": 1.0,
            "description": "Relative importance (0.0–1.0).",
        },
    },
    "additionalProperties": False,
}

_ATTRACTOR_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "description": "Structural and behavioral attractors.",
    "properties": {
        "structural": {
            "type": "array",
            "items": _ATTRACTOR_ITEM_SCHEMA,
            "default": [],
            "description": "Architectural attractor patterns.",
        },
        "behavioral": {
            "type": "array",
            "items": _ATTRACTOR_ITEM_SCHEMA,
            "default": [],
            "description": "Functional attractor patterns.",
        },
    },
    "additionalProperties": False,
}

_TEST_SCENARIO_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "description": "BDD-style test scenario.",
    "required": ["name", "given", "when", "then"],
    "properties": {
        "name": {
            "type": "string",
            "minLength": 1,
            "description": "Scenario name.",
        },
        "given": {
            "type": "string",
            "minLength": 1,
            "description": "Pre-conditions / setup.",
        },
        "when": {
            "type": "string",
            "minLength": 1,
            "description": "Action under test.",
        },
        "then": {
            "type": "string",
            "minLength": 1,
            "description": "Expected outcome.",
        },
        "module": {
            "type": ["string", "null"],
            "description": "Module this scenario targets.",
        },
    },
    "additionalProperties": False,
}

_VERIFICATION_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "description": "Verification and acceptance section.",
    "properties": {
        "test_scenarios": {
            "type": "array",
            "items": _TEST_SCENARIO_SCHEMA,
            "default": [],
            "description": "BDD-style test scenarios.",
        },
        "assertions": {
            "type": "array",
            "items": {"type": "string"},
            "default": [],
            "description": "Global assertion expressions.",
        },
        "acceptance_criteria": {
            "type": "array",
            "items": {"type": "string"},
            "default": [],
            "description": "High-level acceptance criteria.",
        },
    },
    "additionalProperties": False,
}

_METADATA_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "description": "Contract authorship and project metadata.",
    "properties": {
        "author": {
            "type": ["string", "null"],
            "description": "Contract author.",
        },
        "created_at": {
            "type": ["string", "null"],
            "format": "date-time",
            "description": "Creation timestamp (ISO-8601).",
        },
        "updated_at": {
            "type": ["string", "null"],
            "format": "date-time",
            "description": "Last-updated timestamp (ISO-8601).",
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "default": [],
            "description": "Categorisation tags.",
        },
        "language": {
            "type": ["string", "null"],
            "description": "Target programming language.",
        },
        "framework": {
            "type": ["string", "null"],
            "description": "Target framework.",
        },
        "target_directory": {
            "type": ["string", "null"],
            "description": "Filesystem path for generated output.",
        },
    },
    "additionalProperties": False,
}

# ---------------------------------------------------------------------------
# Top-level Language Contract schema
# ---------------------------------------------------------------------------

LANGUAGE_CONTRACT_SCHEMA: Dict[str, Any] = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Language Contract",
    "description": (
        "Top-level schema for a Contract-Coding Language Contract v1.0. "
        "Defines the complete structure for expressing development intent "
        "as a verifiable, parallelizable specification."
    ),
    "type": "object",
    "required": ["intent"],
    "properties": {
        "version": {
            "type": "string",
            "default": "1.0",
            "description": "Contract schema version.",
        },
        "intent": {
            "type": "string",
            "minLength": 1,
            "description": "Natural-language statement of the system's purpose.",
        },
        "description": {
            "type": ["string", "null"],
            "description": "Extended description of the contract scope.",
        },
        "metadata": {
            **_METADATA_SCHEMA,
            "default": {},
        },
        "attractors": {
            **_ATTRACTOR_SCHEMA,
            "default": {},
        },
        "modules": {
            "type": "array",
            "items": _MODULE_CONTRACT_SCHEMA,
            "default": [],
            "description": "Module specifications.",
        },
        "topology": {
            "type": "array",
            "items": _TOPOLOGY_LINK_SCHEMA,
            "default": [],
            "description": "Explicit dependency edges between modules.",
        },
        "verification": {
            **_VERIFICATION_SCHEMA,
            "default": {},
        },
        "global_constraints": {
            "type": "array",
            "items": {"type": "string"},
            "default": [],
            "description": "Contract-wide constraint expressions.",
        },
    },
    "additionalProperties": False,
}


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def get_schema() -> Dict[str, Any]:
    """Return a *copy* of the Language Contract JSON Schema.

    Returns:
        A deep-ish copy of the schema dict (top-level keys are shared
        but the dict itself is new, so callers can safely mutate it).
    """
    import copy

    return copy.deepcopy(LANGUAGE_CONTRACT_SCHEMA)


def get_schema_version() -> str:
    """Return the current schema version string.

    Returns:
        A semver-style version string (e.g. ``"1.0"``).
    """
    return SCHEMA_VERSION


def validate_against_schema(data: Dict[str, Any]) -> List[str]:
    """Validate a dict against the Language Contract JSON Schema.

    This performs *structural* validation only (types, required fields,
    enum values, etc.).  For semantic validation (dependency cycles,
    cross-references, etc.) use ``ContractValidator``.

    Args:
        data: A dict to validate (typically from ``yaml.safe_load`` or
            ``json.loads``).

    Returns:
        A list of human-readable error strings.  An empty list means
        the data is structurally valid.
    """
    validator = jsonschema.Draft7Validator(LANGUAGE_CONTRACT_SCHEMA)
    errors: List[str] = []
    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        path = ".".join(str(p) for p in error.absolute_path) or "<root>"
        errors.append(f"[{path}] {error.message}")
    return errors
