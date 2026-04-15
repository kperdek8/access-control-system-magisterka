import os
from contextlib import asynccontextmanager
from typing import List, Any, Dict

import uvicorn
import requests
from fastapi import FastAPI
from common.schemas import AuthorizationRequest, AuthorizationResponse, Decision, AttributeResponse, AttributeRequest
from common.logger import get_logger
from parser import load_and_parse_policies
from transformer import Rule

logger = get_logger("PDP-SERVICE")
PIP_URL = os.getenv("PIP_URL")

policies: list = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    global policies
    policies = load_and_parse_policies()
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

    logger.info(f"Sending attributes request: {attribute_request} to {PIP_URL}")

    try:
        response = requests.post(
            PIP_URL,
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
        return []


# TODO: Obsługa atrybutów środowiskowych
def policy_engine(subject_attributes: dict, resource_attributes: dict):
    missing_attributes = {
        "subject": set(),
        "resource": set()
    }

    for policy in policies:
        if isinstance(policy, Rule):
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
    }

    final_decision = False

    for policy in policies:
        if isinstance(policy, Rule):
            decision = policy.evaluate(context)
            # TODO: Metody rozwiązywania konfliktów, narazie Permit-Overrides
            if decision == "ALLOW":
                return True

    return False


@app.post("/authorize", response_model=AuthorizationResponse)
def evaluate_decision(request: AuthorizationRequest) -> AuthorizationResponse:
    logger.info(f"Received authorization request: {request}")
    if policy_engine(request.subject, request.resource):
        logger.info(f"Authorization decision: {Decision.PERMIT}")
        return AuthorizationResponse(decision=Decision.PERMIT)
    else:
        logger.info(f"Authorization decision: {Decision.DENY}")
        return AuthorizationResponse(decision=Decision.DENY)

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