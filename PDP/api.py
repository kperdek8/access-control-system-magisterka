import os
from typing import List, Any

import requests
from fastapi import FastAPI
from common.schemas import AuthorizationRequest, AuthorizationResponse, Decision, AttributeResponse, AttributeRequest
from common.logger import get_logger

app = FastAPI()
logger = get_logger("PDP-SERVICE")
PIP_URL = os.getenv("PIP_URL")


def get_attributes(id, type: str, attributes: list[str]) -> List[Any]:
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


def rule_placeholder(subject_attributes: dict, resource_attributes):
    if subject_attributes.get("id") and resource_attributes.get("id") and subject_attributes.get("id") == resource_attributes.get("id"):
        return True
    else:
        if not subject_attributes.get("role"):
            attributes = get_attributes(id=subject_attributes.get("id"), type=subject_attributes.get("type"), attributes=["role"])
            for attribute in attributes:
                subject_attributes.update(attribute)
        if subject_attributes.get("role") == "manager":
            return True
        else:
            return False


@app.post("/authorize", response_model=AuthorizationResponse)
def evaluate_decision(request: AuthorizationRequest) -> AuthorizationResponse:
    logger.info(f"Received authorization request: {request}")
    if rule_placeholder(request.subject, request.resource):
        logger.info(f"Authorization decision: {Decision.PERMIT}")
        return AuthorizationResponse(decision=Decision.PERMIT)
    else:
        logger.info(f"Authorization decision: {Decision.DENY}")
        return AuthorizationResponse(decision=Decision.DENY)

@app.get("/")
def health_check():
    return {"status": "alive", "service": "policy_decision_point"}