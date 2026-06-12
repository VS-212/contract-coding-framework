from typing import List, Dict, Optional
from pydantic import BaseModel, Field, field_validator
import re

class Dependency(BaseModel):
    source: str = Field(..., description="The name of the module that depends on the target")
    target: str = Field(..., description="The name of the module being depended on")
    description: Optional[str] = Field(None, description="Why this dependency exists")

class Constraint(BaseModel):
    name: str = Field(..., description="Identifier for the constraint")
    expression: str = Field(..., description="CEL (Common Expression Language) string evaluating to a boolean")
    description: str = Field(..., description="Human-readable description of the constraint")

class SemanticAttractor(BaseModel):
    name: str = Field(..., description="Name of the module or component (Must start with M-)")
    description: str = Field(..., description="High-level description of what this module does")
    responsibilities: List[str] = Field(default_factory=list, description="Specific responsibilities of this module")
    constraints: List[Constraint] = Field(default_factory=list, description="Local constraints for this module")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not re.match(r"^M-[A-Z0-9\-]+$", v):
            raise ValueError(f"Module name '{v}' must match pattern ^M-[A-Z0-9\\-]+$")
        return v

class VerificationEntry(BaseModel):
    id: str = Field(..., description="Verification ID (Must start with V-M-)")
    module_id: str = Field(..., description="The module this verifies")
    command: str = Field(..., description="Command to execute the test")
    scenarios: List[str] = Field(default_factory=list, description="Testing scenarios")
    
    @field_validator('id')
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not re.match(r"^V-M-[A-Z0-9\-]+$", v):
            raise ValueError(f"Verification ID '{v}' must match pattern ^V-M-[A-Z0-9\\-]+$")
        return v

class TechnologyStack(BaseModel):
    languages: List[str] = Field(default_factory=list)
    frameworks: List[str] = Field(default_factory=list)
    testing_tools: List[str] = Field(default_factory=list)

class LanguageContract(BaseModel):
    version: str = Field(default="1.0", description="Contract version")
    intent: str = Field(..., description="High-level ambiguous intent (vibe coding goal)")
    global_constraints: List[Constraint] = Field(default_factory=list, description="System-wide invariants")
    technology_stack: Optional[TechnologyStack] = Field(default=None, description="Approved technologies")
    verification_plan: List[VerificationEntry] = Field(default_factory=list, description="Verification plans")
    modules: List[SemanticAttractor] = Field(..., description="The semantic attractors (modules) forming the system")
    topology: List[Dependency] = Field(default_factory=list, description="Dependencies between modules")
