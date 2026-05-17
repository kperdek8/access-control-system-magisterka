from datetime import timedelta, datetime

from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from enum import Enum, StrEnum


class Mode(StrEnum):
    DECISION = "DECISION"
    CONSTRAINTS = "CONSTRAINTS"


class Decision(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"


class Behaviour(StrEnum):
    PERMIT_OVERRIDE = "permit_override"
    DENY_OVERRIDE = "deny_override"


class Action(StrEnum):
    READ = "READ"
    WRITE = "WRITE"
    DELETE = "DELETE"
    # SHARE = "SHARE" Po implementacji delegacji


class DelegationSchema(BaseModel):
    active: bool = True
    action: Optional[List[Action]] = None
    delegatee_id: str
    delegatee_type: str
    delegator_id: str
    delegator_type: str
    duration: Optional[timedelta] = None
    start_date: Optional[datetime] = None
    resource_id: str
    resource_type: str


    class Config:
        from_attributes = True


class AuthorizationRequest(BaseModel):
    subject: Dict[str, Any]
    resource: Dict[str, Any]
    action: Action
    mode: Optional[Mode] = None


class AuthorizationResponse(BaseModel):
    decision: Decision
    constraints: Optional[Any] = None


class AttributeRequest(BaseModel):
    id: str
    type: str
    attributes: List[Any]


class BatchAttributeRequest(BaseModel):
    entities: List[AttributeRequest]


class AttributeResponse(BaseModel):
    attributes: Dict[str, Any]


class BatchAttributeResponse(BaseModel):
    attributes: Dict[str, Dict[str, Dict[str, Any]]]


class AddDelegationRequest(BaseModel):
    delegator_id: str
    delegator_type: str
    delegatee_id: str
    delegatee_type: str
    resource_id: str
    resource_type: str
    duration: timedelta
    start_date: datetime
    action: List[Action]


class AddDelegationResponse(BaseModel):
    detail: Optional[str]


class RevokeDelegationRequest(BaseModel):
    delegator_id: str
    delegator_type: str
    delegatee_id: str
    delegatee_type: str
    resource_id: str
    resource_type: str


class RevokeDelegationResponse(BaseModel):
    detail: Optional[str]


class GetDelegationsRequest(BaseModel):
    subject_id: str | int
    subject_type: str
    resource_id: str | int
    resource_type: str


class GetDelegationsResponse(BaseModel):
    delegations: List[DelegationSchema]