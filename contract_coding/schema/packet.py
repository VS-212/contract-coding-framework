from pydantic import BaseModel, Field
from typing import List, Dict, Any

class FailureHandoff(BaseModel):
    last_error: str = Field(default="")
    attempts: int = Field(default=0)
    context_dump: str = Field(default="")

class ExecutionPacket(BaseModel):
    target_node: str = Field(..., description="The node or CohesionNode to execute")
    modules: List[str] = Field(..., description="List of module IDs involved (M-*)")
    stop_conditions: List[str] = Field(default_factory=list, description="Conditions that signify completion")
    retry_budget: int = Field(default=3, description="Max retries before handoff")
    failure_handoff: FailureHandoff = Field(default_factory=FailureHandoff)
