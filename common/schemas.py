from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from enum import Enum


class Decision(str, Enum):
    PERMIT = "PERMIT"
    DENY = "DENY"


class Action(str, Enum):
    READ = "READ"
    WRITE = "WRITE"
    DELETE = "DELETE"
    # SHARE = "SHARE" Po implementacji delegacji


class AuthorizationRequest(BaseModel):
    subject: Dict[str, Any]
    resource: Dict[str, Any]
    action: Action


class AuthorizationResponse(BaseModel):
    decision: Decision


class AttributeRequest(BaseModel):
    id: Optional[int] = None
    type: Optional[str] = None
    attributes: Optional[List[Any]] = None


class AttributeResponse(BaseModel):
    attributes: Dict[str, Any] = None
