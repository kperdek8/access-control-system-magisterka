from typing import Tuple, List

import requests

from common.logger import get_logger
from common.schemas import AddDelegationRequest, AddDelegationResponse, RevokeDelegationResponse, \
    RevokeDelegationRequest, DelegationSchema, GetDelegationsRequest, GetDelegationsResponse

logger = get_logger("PDP-SERVICE")


def add_delegation(pip_url: str, delegation: AddDelegationRequest) -> AddDelegationResponse:
    base_url = pip_url.rstrip("/")
    target_url = f"{base_url}/delegations"
    logger.info(f"Sending request to revoke delegation to {target_url}")

    try:
        response = requests.post(
            target_url,
            data=delegation.model_dump_json(),
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        response.raise_for_status()

        add_delegation_response = AddDelegationResponse(**response.json())
        if response.status_code == 200:
            logger.info(f"Delegation added successfully")
        else:
            logger.info(f"Delegation addition failed")

        return add_delegation_response

    except requests.exceptions.RequestException as e:
        logger.error(f"Error during communication with PIP: {e}")
        return AddDelegationResponse(details="Server-side error, contact administrator.")


def revoke_delegation(pip_url: str, delegation: RevokeDelegationRequest) -> Tuple[int, RevokeDelegationResponse]:
    base_url = pip_url.rstrip("/")
    target_url = f"{base_url}/delegations"
    logger.info(f"Sending request to revoke delegation to {target_url}")

    try:
        response = requests.patch(
            target_url,
            data=delegation.model_dump_json(),
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        response.raise_for_status()

        revoke_delegation_response = RevokeDelegationResponse(**response.json())
        if response.status_code == 200:
            logger.info(f"Delegation revoked successfully")
            return response.status_code, revoke_delegation_response
        else:
            logger.info(f"Delegation revocation failed")
            return response.status_code, revoke_delegation_response

    except requests.exceptions.RequestException as e:
        logger.error(f"Error during communication with PIP: {e}")
        return 500, RevokeDelegationResponse(details="Server-side error, contact administrator.")


def get_delegations(pip_url: str, subject_id, subject_type, resource_id, resource_type) -> List[DelegationSchema]:
    base_url = pip_url.rstrip("/")
    target_url = f"{base_url}/delegations"
    logger.info(f"Sending request to get existing delegations for subject {subject_type}:{subject_id} and resource {resource_type}:{resource_id}")

    request = GetDelegationsRequest(
        subject_id=subject_id,
        subject_type=subject_type,
        resource_id=resource_id,
        resource_type=resource_type
    )

    try:
        response = requests.get(
            target_url,
            params=request,
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        response.raise_for_status()

        delegations_response = GetDelegationsResponse(**response.json())
        logger.info(f"Received delegations {delegations_response.delegations}")

        return delegations_response.delegations

    except requests.exceptions.RequestException as e:
        logger.error(f"Error during communication with PIP: {e}")
        return []
