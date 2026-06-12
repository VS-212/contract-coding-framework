"""Contract parser supporting YAML, JSON, and mixed-format input.

This module provides ``ContractParser``, a robust parser that can read
Language Contract specifications from files (auto-detecting format),
raw strings, or pre-parsed dicts.  It also supports:

* **Local ``$ref`` resolution** – references of the form
  ``{"$ref": "#/path/to/node"}`` are resolved against the document root
  before Pydantic validation.
* **Contract inheritance** – an ``extends`` key at the top level names a
  base contract file whose values are deep-merged with the current one.

Classes:
    ContractParser: Stateless parser with ``parse_file``, ``parse_string``,
        and ``parse_dict`` entry points.

Exceptions:
    ContractParseError: Raised for any parse-time failure, with structured
        context (filename, line number when available, detail message).

Usage:
    >>> from contract_coding.core.parser import ContractParser
    >>> parser = ContractParser()
    >>> contract = parser.parse_file("my_contract.yaml")
"""

from __future__ import annotations

import json
import re
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

import yaml

from contract_coding.core.contract import LanguageContract


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ContractParseError(Exception):
    """Raised when a contract cannot be parsed.

    Attributes:
        message: Description of the error.
        path: Filesystem path of the file that caused the error (if any).
        line: 1-based line number where the error occurred (if known).
        detail: Additional technical detail (e.g. the underlying exception).
    """

    def __init__(
        self,
        message: str,
        *,
        path: Optional[Union[str, Path]] = None,
        line: Optional[int] = None,
        detail: Optional[str] = None,
    ) -> None:
        self.message = message
        self.path = Path(path) if path else None
        self.line = line
        self.detail = detail
        parts: list[str] = []
        if self.path:
            parts.append(f"file={self.path}")
        if self.line is not None:
            parts.append(f"line={self.line}")
        location = f" ({', '.join(parts)})" if parts else ""
        full = f"{message}{location}"
        if detail:
            full += f"\n  Detail: {detail}"
        super().__init__(full)


# ---------------------------------------------------------------------------
# Format enum
# ---------------------------------------------------------------------------

class ContractFormat(str, Enum):
    """Supported contract serialization formats."""

    YAML = "yaml"
    JSON = "json"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _detect_format(path: Path) -> ContractFormat:
    """Infer the contract format from a file's extension.

    Args:
        path: File path to inspect.

    Returns:
        The detected ``ContractFormat``.

    Raises:
        ContractParseError: If the extension is not recognised.
    """
    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        return ContractFormat.YAML
    if suffix in {".json"}:
        return ContractFormat.JSON
    raise ContractParseError(
        f"Cannot detect format from extension '{suffix}'",
        path=path,
        detail="Supported extensions: .yaml, .yml, .json",
    )


def _detect_format_from_content(content: str) -> ContractFormat:
    """Heuristically detect format from raw string content.

    JSON documents start with ``{`` (ignoring leading whitespace).
    Everything else is treated as YAML.

    Args:
        content: Raw file content.

    Returns:
        The detected ``ContractFormat``.
    """
    stripped = content.lstrip()
    if stripped.startswith("{"):
        return ContractFormat.JSON
    return ContractFormat.YAML


def _parse_yaml(content: str, *, path: Optional[Path] = None) -> Dict[str, Any]:
    """Parse YAML content into a dict with good error messages.

    Args:
        content: Raw YAML string.
        path: Optional source file path (used in error messages).

    Returns:
        A parsed dict.

    Raises:
        ContractParseError: On YAML syntax errors.
    """
    try:
        data = yaml.safe_load(content)
    except yaml.MarkedYAMLError as exc:
        line = exc.problem_mark.line + 1 if exc.problem_mark else None
        raise ContractParseError(
            "YAML syntax error",
            path=path,
            line=line,
            detail=str(exc),
        ) from exc
    except yaml.YAMLError as exc:
        raise ContractParseError(
            "YAML parsing failed",
            path=path,
            detail=str(exc),
        ) from exc

    if data is None:
        raise ContractParseError("YAML file is empty", path=path)
    if not isinstance(data, dict):
        raise ContractParseError(
            f"Expected a YAML mapping at the top level, got {type(data).__name__}",
            path=path,
        )
    return data


def _parse_json(content: str, *, path: Optional[Path] = None) -> Dict[str, Any]:
    """Parse JSON content into a dict with good error messages.

    Args:
        content: Raw JSON string.
        path: Optional source file path (used in error messages).

    Returns:
        A parsed dict.

    Raises:
        ContractParseError: On JSON syntax errors.
    """
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ContractParseError(
            "JSON syntax error",
            path=path,
            line=exc.lineno,
            detail=exc.msg,
        ) from exc

    if not isinstance(data, dict):
        raise ContractParseError(
            f"Expected a JSON object at the top level, got {type(data).__name__}",
            path=path,
        )
    return data


# ---------------------------------------------------------------------------
# $ref resolution
# ---------------------------------------------------------------------------

def _resolve_refs(data: Any, root: Dict[str, Any]) -> Any:
    """Recursively resolve local ``$ref`` pointers in *data*.

    A ``$ref`` must be a string of the form ``#/path/to/node`` where each
    segment is a dict key.  Array indices are **not** supported.

    Args:
        data: The (sub-)document to resolve.
        root: The full document root used for look-ups.

    Returns:
        A new data structure with all ``$ref`` occurrences replaced by
        the referenced value.

    Raises:
        ContractParseError: If a ``$ref`` target cannot be found.
    """
    if isinstance(data, dict):
        if "$ref" in data and isinstance(data["$ref"], str):
            ref: str = data["$ref"]
            return _dereference(ref, root)
        return {k: _resolve_refs(v, root) for k, v in data.items()}
    if isinstance(data, list):
        return [_resolve_refs(item, root) for item in data]
    return data


def _dereference(ref: str, root: Dict[str, Any]) -> Any:
    """Look up a JSON-pointer-style ``$ref`` in the document root.

    Args:
        ref: A reference string (e.g. ``"#/definitions/VarSchema"``).
        root: The document root dict.

    Returns:
        The resolved value.

    Raises:
        ContractParseError: If the path is invalid or cannot be found.
    """
    if not ref.startswith("#/"):
        raise ContractParseError(
            f"Unsupported $ref format: '{ref}'",
            detail="Only local references starting with '#/' are supported.",
        )
    parts = ref[2:].split("/")
    current: Any = root
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            raise ContractParseError(
                f"Cannot resolve $ref '{ref}': key '{part}' not found",
            )
    return current


# ---------------------------------------------------------------------------
# Contract inheritance / extends
# ---------------------------------------------------------------------------

def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep-merge *override* into *base*, returning a new dict.

    Rules:
    * Dict values are merged recursively.
    * List values in *override* **replace** the base (no concatenation,
      which could cause confusing duplicates).
    * Scalar values in *override* replace the base.

    Args:
        base: The base mapping.
        override: The override mapping.

    Returns:
        A new merged dict.
    """
    merged = dict(base)
    for key, value in override.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _apply_extends(
    data: Dict[str, Any],
    *,
    base_dir: Optional[Path] = None,
    seen: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """Process the ``extends`` key for contract inheritance.

    The ``extends`` value is a relative or absolute path to a base
    contract file.  The base is loaded, *its own* ``extends`` resolved
    recursively, and then *data* is deep-merged on top of the base.

    Args:
        data: Current contract dict (may contain ``extends``).
        base_dir: Directory used to resolve relative ``extends`` paths.
        seen: Set of already-visited absolute paths to detect cycles.

    Returns:
        A new dict with the ``extends`` chain fully resolved.

    Raises:
        ContractParseError: On missing files, cycles, or parse errors.
    """
    extends_path = data.pop("extends", None)
    if extends_path is None:
        return data

    if seen is None:
        seen = set()

    resolved = Path(extends_path)
    if not resolved.is_absolute() and base_dir is not None:
        resolved = base_dir / resolved
    resolved = resolved.resolve()

    canonical = str(resolved)
    if canonical in seen:
        raise ContractParseError(
            f"Circular extends chain detected: '{canonical}' has already been visited",
        )
    seen.add(canonical)

    if not resolved.exists():
        raise ContractParseError(
            f"Base contract not found: '{resolved}'",
            detail=f"Referenced via extends: '{extends_path}'",
        )

    base_content = resolved.read_text(encoding="utf-8")
    fmt = _detect_format(resolved)
    if fmt is ContractFormat.YAML:
        base_data = _parse_yaml(base_content, path=resolved)
    else:
        base_data = _parse_json(base_content, path=resolved)

    # Recurse into the base's own extends.
    base_data = _apply_extends(base_data, base_dir=resolved.parent, seen=seen)

    return _deep_merge(base_data, data)


# ---------------------------------------------------------------------------
# ContractParser
# ---------------------------------------------------------------------------

class ContractParser:
    """Stateless parser that produces validated ``LanguageContract`` instances.

    The parser supports YAML and JSON input, auto-detects format from file
    extensions or content heuristics, resolves local ``$ref`` pointers,
    and handles contract inheritance via ``extends``.

    Example::

        parser = ContractParser()
        contract = parser.parse_file("path/to/contract.yaml")
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse_file(self, path: Union[str, Path]) -> LanguageContract:
        """Parse a contract from a file on disk.

        The format is auto-detected from the file extension (``.yaml``,
        ``.yml``, ``.json``).

        Args:
            path: Path to the contract file.

        Returns:
            A validated ``LanguageContract``.

        Raises:
            ContractParseError: On I/O errors, syntax errors, or
                validation failures.
        """
        filepath = Path(path).resolve()
        if not filepath.exists():
            raise ContractParseError(
                f"File not found: '{filepath}'",
                path=filepath,
            )
        if not filepath.is_file():
            raise ContractParseError(
                f"Path is not a file: '{filepath}'",
                path=filepath,
            )

        content = filepath.read_text(encoding="utf-8")
        fmt = _detect_format(filepath)
        data = self._parse_raw(content, fmt, path=filepath)

        # Resolve extends chain.
        data = _apply_extends(data, base_dir=filepath.parent)

        # Resolve $ref pointers.
        data = _resolve_refs(data, data)

        return self._validate(data, path=filepath)

    def parse_string(
        self,
        content: str,
        fmt: Optional[Union[str, ContractFormat]] = None,
    ) -> LanguageContract:
        """Parse a contract from a raw string.

        Args:
            content: The raw YAML or JSON string.
            fmt: Explicit format (``"yaml"`` or ``"json"``).  When
                ``None`` the format is detected from the content.

        Returns:
            A validated ``LanguageContract``.

        Raises:
            ContractParseError: On syntax or validation errors.
        """
        if fmt is None:
            resolved_fmt = _detect_format_from_content(content)
        elif isinstance(fmt, str):
            try:
                resolved_fmt = ContractFormat(fmt.lower())
            except ValueError:
                raise ContractParseError(
                    f"Unsupported format: '{fmt}'",
                    detail="Supported formats: yaml, json",
                )
        else:
            resolved_fmt = fmt

        data = self._parse_raw(content, resolved_fmt)

        # $ref resolution only (no extends without a file context).
        data = _resolve_refs(data, data)

        return self._validate(data)

    def parse_dict(self, data: Dict[str, Any]) -> LanguageContract:
        """Parse a contract from a pre-parsed dict.

        Args:
            data: A dict matching the Language Contract structure.

        Returns:
            A validated ``LanguageContract``.

        Raises:
            ContractParseError: On validation errors.
        """
        if not isinstance(data, dict):
            raise ContractParseError(
                f"Expected a dict, got {type(data).__name__}",
            )
        resolved = _resolve_refs(data, data)
        return self._validate(resolved)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_raw(
        content: str,
        fmt: ContractFormat,
        *,
        path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Dispatch to the correct low-level parser.

        Args:
            content: Raw string.
            fmt: Target format.
            path: Optional file path for error messages.

        Returns:
            Parsed dict.
        """
        if fmt is ContractFormat.YAML:
            return _parse_yaml(content, path=path)
        return _parse_json(content, path=path)

    @staticmethod
    def _validate(
        data: Dict[str, Any],
        *,
        path: Optional[Path] = None,
    ) -> LanguageContract:
        """Run Pydantic validation and wrap errors in ``ContractParseError``.

        Args:
            data: Parsed dict.
            path: Optional source file path for error context.

        Returns:
            A validated ``LanguageContract`` instance.

        Raises:
            ContractParseError: If Pydantic validation fails, with a
                human-readable summary of all errors.
        """
        try:
            return LanguageContract.model_validate(data)
        except Exception as exc:
            # Build a readable error summary from Pydantic's ValidationError.
            detail_lines: list[str] = []
            if hasattr(exc, "errors"):
                for err in exc.errors():  # type: ignore[union-attr]
                    loc = " → ".join(str(l) for l in err.get("loc", []))
                    msg = err.get("msg", str(err))
                    detail_lines.append(f"  [{loc}] {msg}")
            detail = "\n".join(detail_lines) if detail_lines else str(exc)
            raise ContractParseError(
                "Contract validation failed",
                path=path,
                detail=detail,
            ) from exc
