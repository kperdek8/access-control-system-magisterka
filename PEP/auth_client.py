import os
from common import schemas
from common.logger import get_logger
from typing import Dict, Any
import requests


PDP_URL = os.getenv("PDP_URL")
logger = get_logger("PEP_SERVICE")


def verify_authorization(subject: Dict[str, Any], resource: Dict[str, Any], action: str) -> bool:
    """
    Wysyła zapytanie o autoryzację do PDP i zwraca True jeżeli decyzja to PERMIT.
    """
    auth_request = schemas.AuthorizationRequest(
        subject=subject,
        resource=resource,
        action=action
    )

    logger.info(f"Sending authorization request: {auth_request} to {PDP_URL}")

    try:
        response = requests.post(
            PDP_URL,
            data=auth_request.model_dump_json(),
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        response.raise_for_status()

        auth_response = schemas.AuthorizationResponse(**response.json())
        logger.info(f"Received authorization response. Decision: {auth_response.decision}")

        return auth_response.decision == schemas.Decision.PERMIT

    except requests.exceptions.RequestException as e:
        logger.error(f"Error during communication with PDP: {e}")
        return False
