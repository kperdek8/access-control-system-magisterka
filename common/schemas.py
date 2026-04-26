from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from enum import Enum, StrEnum


class Mode(StrEnum):
    DECISION = "DECISION"
    CONSTRAINTS = "CONSTRAINTS"


class Decision(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"


class Action(StrEnum):
    READ = "READ"
    WRITE = "WRITE"
    DELETE = "DELETE"
    # SHARE = "SHARE" Po implementacji delegacji


class AuthorizationRequest(BaseModel):
    subject: Dict[str, Any]
    resource: Dict[str, Any]
    action: Action
    mode: Optional[Mode] = None


class AuthorizationResponse(BaseModel):
    decision: Decision
    constraints: Optional[Any] = None


class AttributeRequest(BaseModel):
    id: int
    type: str
    attributes: List[Any]


class AttributeResponse(BaseModel):
    attributes: Dict[str, Any]
