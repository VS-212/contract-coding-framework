"""Core module: Language Contract schema, parser, and validator.

Public API re-exports
---------------------

Models (``contract.py``):
    VarSchema, ConstraintSchema, TopologyLink, ModuleContract,
    AttractorItem, AttractorSchema, TestScenario, VerificationSchema,
    MetadataSchema, LanguageContract, LinkType, AttractorType

Schema (``schema.py``):
    LANGUAGE_CONTRACT_SCHEMA, SCHEMA_VERSION,
    get_schema, get_schema_version, validate_against_schema

Parser (``parser.py``):
    ContractParser, ContractParseError, ContractFormat

Validator (``validator.py``):
    ContractValidator, ValidationResult, ValidationMessage,
    ValidationError, ValidationWarning, Severity
"""

from contract_coding.core.contract import (
    AttractorItem,
    AttractorSchema,
    AttractorType,
    ConstraintSchema,
    LanguageContract,
    LinkType,
    MetadataSchema,
    ModuleContract,
    TestScenario,
    TopologyLink,
    VarSchema,
    VerificationSchema,
)
from contract_coding.core.parser import (
    ContractFormat,
    ContractParseError,
    ContractParser,
)
from contract_coding.core.schema import (
    LANGUAGE_CONTRACT_SCHEMA,
    SCHEMA_VERSION,
    get_schema,
    get_schema_version,
    validate_against_schema,
)
from contract_coding.core.validator import (
    ContractValidator,
    Severity,
    ValidationError,
    ValidationMessage,
    ValidationResult,
    ValidationWarning,
)

__all__ = [
    # Models
    "VarSchema",
    "ConstraintSchema",
    "TopologyLink",
    "ModuleContract",
    "AttractorItem",
    "AttractorSchema",
    "AttractorType",
    "TestScenario",
    "VerificationSchema",
    "MetadataSchema",
    "LanguageContract",
    "LinkType",
    # Schema
    "LANGUAGE_CONTRACT_SCHEMA",
    "SCHEMA_VERSION",
    "get_schema",
    "get_schema_version",
    "validate_against_schema",
    # Parser
    "ContractParser",
    "ContractParseError",
    "ContractFormat",
    # Validator
    "ContractValidator",
    "ValidationResult",
    "ValidationMessage",
    "ValidationError",
    "ValidationWarning",
    "Severity",
]
