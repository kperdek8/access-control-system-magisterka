import os
from typing import Any, Dict, List, Set

import requests

from common.logger import get_logger
from common.schemas import AttributeRequest, AttributeResponse, BatchAttributeResponse, BatchAttributeRequest

logger = get_logger("PDP-SERVICE")
#logger.setLevel("DEBUG")


def get_attributes(pip_url: str, id, type: str, attributes: Set[str]) -> Dict[str, Any]:
    """
    Wysyła zapytanie do PIP o atrybuty.
    """
    attribute_request = AttributeRequest(
        id=id,
        type=type,
        attributes=attributes
    )

    base_url = pip_url.rstrip("/")
    target_url = f"{base_url}/attributes"
    logger.info(f"Sending attributes request: {attribute_request} to {pip_url}")

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


def get_attributes_batch(pip_url: str, entities_to_fetch: List[Dict[str, Any]]) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """
    Wysyła zbiorcze (batchowe) zapytanie do PIP o atrybuty wielu podmiotów/zasobów na raz.

    Argument `entities_to_fetch` powinien być listą słowników o strukturze:
    [
        {"id": "doc_1", "type": "document", "attributes": ["owner", "security_level"]},
        {"id": "user_99", "type": "user", "attributes": ["department"]}
    ]
    """
    if not entities_to_fetch:
        return {}

    requests_list = []
    for entity in entities_to_fetch:
        requests_list.append(
            AttributeRequest(
                id=str(entity["id"]),
                type=entity["type"],
                attributes=list(entity["attributes"])
            )
        )

    batch_request = BatchAttributeRequest(entities=requests_list)

    base_url = pip_url.rstrip("/")
    target_url = f"{base_url}/attributes/batch"
    logger.info(f"Sending batch attributes request for {len(requests_list)} entities to {target_url}")

    try:
        response = requests.post(
            target_url,
            data=batch_request.model_dump_json(),
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        response.raise_for_status()

        batch_response = BatchAttributeResponse(**response.json())
        logger.info(f"Received attributes for {len(batch_response.attributes.keys())} types of entities.")

        return batch_response.attributes

    except requests.exceptions.RequestException as e:
        logger.error(f"Error during batch communication with PIP: {e}")
        return {}