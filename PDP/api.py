import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Any, Dict
from exceptions import SchemaMappingNotFoundError, SelfDelegationNotAllowedError, DurationExceededLimitError
import uvicorn
import requests
from fastapi import FastAPI, HTTPException

from common.registry import SchemaRegistry
from delegations import add_delegation, revoke_delegation, get_delegations
from common.schemas import AuthorizationRequest, AuthorizationResponse, Decision, Mode, AttributeResponse, \
    AttributeRequest, Behaviour, AddDelegationResponse, RevokeDelegationResponse, AddDelegationRequest, \
    RevokeDelegationRequest
from common.logger import get_logger
from common.settings import Settings
from parser import load_and_parse_policies, PolicyStore
from transformer import Rule, DelegationRule

logger = get_logger("PDP-SERVICE")
#logger.setLevel("DEBUG")
PIP_URL = os.getenv("PIP_URL")
resource_schema_path = os.getenv("RESOURCE_SCHEMA_PATH")

schema_registry: SchemaRegistry
policies: PolicyStore
behaviour: Behaviour


@asynccontextmanager
async def lifespan(app: FastAPI):
    global policies
    global behaviour
    global schema_registry
    schema_registry = SchemaRegistry(path=resource_schema_path)
    policies = load_and_parse_policies(schema_registry=schema_registry)
    settings_path = os.getenv("SETTINGS_PATH")
    settings = Settings(settings_path)
    behaviour = settings.get_pdp_mode()
    if behaviour not in [Behaviour.PERMIT_OVERRIDE, Behaviour.DENY_OVERRIDE]:
        raise RuntimeError(f"Invalid behaviour in settings file. Please use '{Behaviour.DENY_OVERRIDE}' or '{Behaviour.PERMIT_OVERRIDE}'.")
    else:
        logger.info(f"PDP started with mode: {behaviour}")
    yield

app = FastAPI(lifespan=lifespan)


def get_attributes(id, type: str, attributes: set[str]) -> dict[str, Any]:
    """
    Wysyła zapytanie do PIP o atrybuty.
    """
    attribute_request = AttributeRequest(
        id=id,
        type=type,
        attributes=attributes
    )

    base_url = PIP_URL.rstrip("/")
    target_url = f"{base_url}/attributes"
    logger.info(f"Sending attributes request: {attribute_request} to {PIP_URL}")

    try:
        response = requests.post(
            target_url,
            data=attribute_request.model_dump_json(),
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        response.raise_for_status()

        attributes_response = AttributeResponse(**response.json())
        logger.info(f"Received attributes {attributes_response.attributes}")

        return attributes_response.attributes

    except requests.exceptions.RequestException as e:
        logger.error(f"Error during communication with PIP: {e}")
        return {}


def evaluate_delegation_request(request: AddDelegationRequest):
    schemas = [request.resource_type, request.delegatee_type, request.delegator_type]
    for schema in schemas:
        if not schema_registry.get_mapping(schema):
            raise SchemaMappingNotFoundError(entity_type=schema)

    if request.delegator_type == request.delegatee_type and request.delegator_id == request.delegatee_id:
            raise SelfDelegationNotAllowedError

    action = request.action[0] if isinstance(request.action, list) else request.action
    applicable_rules = policies.find_delegation(res_type=request.resource_type,
                                                delegatee_type=request.delegatee_type,
                                                delegator_type=request.delegator_type,
                                                action=action)

    resource_primary_key = schema_registry.get_primary_key_for_type(res_type=request.resource_type)
    delegator_primary_key = schema_registry.get_primary_key_for_type(res_type=request.delegator_type)
    delegatee_primary_key = schema_registry.get_primary_key_for_type(res_type=request.delegatee_type)

    attributes = {
        "resource": {resource_primary_key: request.resource_id, "type": request.resource_type},
        "delegator": {delegator_primary_key: request.delegator_id, "type": request.delegator_type},
        "delegatee": {delegatee_primary_key: request.delegatee_id, "type": request.delegatee_type}
    }

    missing_attributes = {
        "resource": set(),
        "delegatee": set(),
        "delegator": set()
    }

    for delegation_rule in applicable_rules:
        for category, attr_name in delegation_rule.rule.collect_attributes():
            if category == "resource" and attr_name not in attributes["resource"]:
                missing_attributes["resource"].add(attr_name)
            elif category == "delegatee" and attr_name not in attributes["delegatee"]:
                missing_attributes["delegatee"].add(attr_name)
            elif category == "delegator" and attr_name not in attributes["delegator"]:
                missing_attributes["delegator"].add(attr_name)

    logger.debug(f"Missing attributes {missing_attributes}")

    if missing_attributes["resource"]:
        attributes["resource"].update(get_attributes(attributes["resource"][resource_primary_key], attributes["resource"]["type"], missing_attributes["resourcet"]))
    if missing_attributes["delegatee"]:
        attributes["delegatee"].update(get_attributes(attributes["delegatee"][resource_primary_key], attributes["delegatee"]["type"], missing_attributes["delegatee"]))
    if missing_attributes["delegator"]:
        attributes["delegator"].update(get_attributes(attributes["delegator"][resource_primary_key], attributes["delegator"]["type"], missing_attributes["delegator"]))

    context = {
        "resource": attributes["resource"],
        "delegatee": attributes["delegatee"],
        "delegator": attributes["delegator"],
        "context": {"action": request.action}
    }

    for delegation_rule in applicable_rules:
        if delegation_rule.rule.evaluate(context=context):
            return True
    return False


def evaluate_decision(subject_attributes: dict, resource_attributes: dict, request_context: dict):
    missing_attributes = {
        "subject": set(),
        "resource": set()
    }

    for policy in policies.rules:
        for category, attr_name in policy.collect_attributes():
            if category == "subject" and attr_name not in subject_attributes:
                missing_attributes["subject"].add(attr_name)
            elif category == "resource" and attr_name not in resource_attributes:
                missing_attributes["resource"].add(attr_name)

    logger.debug(f"Missing attributes {missing_attributes}")

    if missing_attributes["subject"]:
        subject_attributes.update(get_attributes(subject_attributes["id"], subject_attributes["type"], missing_attributes["subject"]))
    if missing_attributes["resource"]:
        resource_attributes.update(get_attributes(resource_attributes["id"], resource_attributes["type"], missing_attributes["resource"]))

    context = {
        "subject": subject_attributes,
        "resource": resource_attributes,
        "context": request_context
    }

    final_decision = False  # Domyślnie zakaz

    for policy in policies.rules:
        decision = policy.evaluate(context)
        if decision == "ALLOW" and behaviour == Behaviour.PERMIT_OVERRIDE:
            return True
        elif decision == "ALLOW" and behaviour == Behaviour.PERMIT_OVERRIDE:
            final_decision = True
        elif decision == "DENY" and behaviour == Behaviour.DENY_OVERRIDE:
            return False

    applicable_delegation_rules = policies.find_delegation_by_delegatee(res_type=resource_attributes["type"], delegatee_type=subject_attributes["type"], action=request_context["action"])
    if not final_decision and applicable_delegation_rules:
        delegations = get_delegations(pip_url=PIP_URL,
                                      subject_id=subject_attributes["id"],
                                      subject_type=subject_attributes["type"],
                                      resource_id=resource_attributes["id"],
                                      resource_type=resource_attributes["type"]
                                      )
        # TODO: Możliwość ciągłej weryfikacji
        if delegations:
            final_decision = True
            logger.info(f"Access granted based on delegation: {delegations[0]}")

    return final_decision


def evaluate_constraints(subject_attributes: dict, resource_attributes: dict, context: dict):
    missing_attributes = {
        "subject": set()
    }

    for policy in policies.rules:
        for category, attr_name in policy.collect_attributes():
            if category == "subject" and attr_name not in subject_attributes:
                missing_attributes["subject"].add(attr_name)

    logger.debug(f"Missing attributes {missing_attributes}")

    if missing_attributes["subject"]:
        subject_attributes.update(get_attributes(subject_attributes["id"], subject_attributes["type"], missing_attributes["subject"]))

    context = {
        "subject": subject_attributes,
        "resource": resource_attributes,
        "context": context
    }

    for policy in policies.rules:
        action, constraints = policy.collect_constraints(context)
        if action == "ALLOW":
            return Decision.ALLOW, constraints

    return Decision.DENY, []


@app.post("/authorize", response_model=AuthorizationResponse)
def authorize(request: AuthorizationRequest) -> AuthorizationResponse:
    logger.info(f"Received authorization request: {request}")
    context = {
        "action": request.action
    }
    if not request.mode or request.mode == Mode.DECISION:
        if evaluate_decision(request.subject, request.resource, context):
            logger.info(f"Authorization decision: {Decision.ALLOW}")
            return AuthorizationResponse(decision=Decision.ALLOW)
        else:
            logger.info(f"Authorization decision: {Decision.DENY}")
            return AuthorizationResponse(decision=Decision.DENY)
    else:
        decision, constraints = evaluate_constraints(request.subject, request.resource, context)
        return AuthorizationResponse(decision=decision, constraints=constraints)


@app.post("/delegations", response_model=AddDelegationResponse)
def add_delegation_endpoint(request: AddDelegationRequest):
    if request.start_date + request.duration < datetime.now():
        raise HTTPException(status_code=400, detail="Delegation already expired.")
    try:
        if evaluate_delegation_request(request=request):
            status_code, result = add_delegation(pip_url=PIP_URL, delegation=request)
            if status_code != 200:
                raise HTTPException(status_code=status_code, detail=result)
            return AddDelegationResponse(detail=result)
        else:
            raise HTTPException(status_code=403, detail="Policy does not allow for this delegation of permissions.")
    except SchemaMappingNotFoundError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except SelfDelegationNotAllowedError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DurationExceededLimitError as e:
        raise HTTPException(status_code=403, detail=str(e))


@app.patch("/delegations/revoke", response_model=RevokeDelegationResponse)
def revoke_delegation_endpoint(request: RevokeDelegationRequest):
    status_code, result = revoke_delegation(pip_url=PIP_URL, delegation=request)

    if status_code != 200:
        raise HTTPException(status_code=status_code, detail=result)

    return result


@app.get("/")
def health_check():
    return {"status": "alive", "service": "policy_decision_point"}


if __name__ == "__main__":
    # Uruchomienie serwera
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8001
    )