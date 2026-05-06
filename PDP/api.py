import os
from contextlib import asynccontextmanager
from typing import List, Any, Dict

import uvicorn
import requests
from fastapi import FastAPI, HTTPException

from delegations import add_delegation, revoke_delegation, get_delegations
from common.schemas import AuthorizationRequest, AuthorizationResponse, Decision, Mode, AttributeResponse, \
    AttributeRequest, Behaviour, AddDelegationResponse, RevokeDelegationResponse, AddDelegationRequest, \
    RevokeDelegationRequest
from common.logger import get_logger
from common.settings import Settings
from parser import load_and_parse_policies
from transformer import Rule

logger = get_logger("PDP-SERVICE")
PIP_URL = os.getenv("PIP_URL")

policies: list = []
behaviour: Behaviour


@asynccontextmanager
async def lifespan(app: FastAPI):
    global policies
    global behaviour
    policies = load_and_parse_policies()
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


def evaluate_decision(subject_attributes: dict, resource_attributes: dict, context: dict):
    missing_attributes = {
        "subject": set(),
        "resource": set()
    }

    for policy in policies:
        if isinstance(policy, Rule):
            for category, attr_name in policy.collect_attributes():
                if category == "context" and attr_name not in context:
                    pass
                elif category == "subject" and attr_name not in subject_attributes:
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
        "context": context
    }

    final_decision = False  # Domyślnie zakaz

    for policy in policies:
        if isinstance(policy, Rule):
            decision = policy.evaluate(context)
            if decision == "ALLOW" and behaviour == Behaviour.PERMIT_OVERRIDE:
                return True
            elif decision == "ALLOW" and behaviour == Behaviour.PERMIT_OVERRIDE:
                final_decision = True
            elif decision == "DENY" and behaviour == Behaviour.DENY_OVERRIDE:
                return False

    if not final_decision:
        delegations = get_delegations(pip_url=PIP_URL,
                                      subject_id=subject_attributes["id"],
                                      subject_type=subject_attributes["type"],
                                      resource_id=resource_attributes["id"],
                                      resource_type=resource_attributes["type"]
                                      )
        if delegations:
            final_decision = True
            logger.info(f"Access granted based on delegation: {delegations[0]}")

    return final_decision


def evaluate_constraints(subject_attributes: dict, resource_attributes: dict, context: dict):
    missing_attributes = {
        "subject": set()
    }

    for policy in policies:
        if isinstance(policy, Rule):
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

    for policy in policies:
        if isinstance(policy, Rule):
            action, constraints = policy.collect_constraints(context)
            print(f"Action: {action} \n Constraints: {constraints}")
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


# TODO: Weryfikacja
@app.post("/delegations", response_model=AddDelegationResponse)
def add_delegation_endpoint(request: AddDelegationRequest):
    status_code, result = add_delegation(pip_url=PIP_URL, delegation=request)
    if status_code != 200:
        raise HTTPException(status_code=status_code, detail=result)
    return result


# TODO: Weryfikacja
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