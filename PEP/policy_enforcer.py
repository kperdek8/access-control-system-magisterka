import os

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from common.logger import get_logger
from common.schemas import Decision
from common.registry import SchemaRegistry
from dotenv import load_dotenv
import requests

load_dotenv()
PDP_URL = os.getenv("PDP_URL")
logger = get_logger("PEP_SERVICE")

security = HTTPBearer()


resource_schema_path = os.getenv("RESOURCE_SCHEMA_PATH")
schema_registry = SchemaRegistry(path=resource_schema_path)


def get_subject_id(res: HTTPAuthorizationCredentials = Depends(security)) -> int:
    """Wyciąga ID użytkownika z tokena Bearer."""
    try:
        return int(res.credentials)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format. Expected integer ID.",
            headers={"WWW-Authenticate": "Bearer"},
        )


class PolicyEnforcer:
    def __init__(self, action: str, resource_type: str, subject_type: str, error_msg: str = "Access Denied"):
        self.action = action
        self.resource_type = resource_type
        self.subject_type = subject_type
        self.error_msg = error_msg
        self._validate_types()

    def _validate_types(self):
        valid_types = schema_registry.get_resource_types()
        if self.subject_type not in valid_types:
            raise RuntimeError(
                f"Configuration Error: Subject type '{self.resource_type}' has not been found in Schema Registry"
            )
        if self.resource_type not in valid_types:
            raise RuntimeError(
                f"Configuration Error: Resource type '{self.resource_type}' has not been found in Schema Registry"
            )

    def __call__(self, resource_id: int, subject_id: int = Depends(get_subject_id)) -> bool:
        auth_request = {
            "subject": {"id": str(subject_id), "type": self.subject_type},
            "resource": {"id": str(resource_id), "type": self.resource_type},
            "action": self.action
        }

        logger.info(f"Verifying {self.action} on {self.resource_type}:{resource_id} by subject {self.subject_type}:{subject_id}")

        try:
            response = requests.post(
                PDP_URL,
                json=auth_request,
                timeout=5
            )
            response.raise_for_status()

            data = response.json()
            if data.get("decision") == Decision.ALLOW:
                return True

        except Exception as e:
            logger.error(f"PDP communication error: {e}")

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=self.error_msg
        )