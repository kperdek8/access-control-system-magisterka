import os

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import requests
from sqlalchemy import or_, and_

from policy_enforcer import schema_registry
from common.logger import get_logger
from common.schemas import Decision, Mode

load_dotenv()
PDP_URL = os.getenv("PDP_URL")
security = HTTPBearer()
logger = get_logger("PEP_SERVICE")


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


def sql_apply_constraints(query, model, constraints: list[list[dict]]):
    """
    Tłumaczy listę list (DNF) na klauzule WHERE SQLAlchemy.
    Format: [[{cond1}, {cond2}], [{cond3}]] -> (cond1 AND cond2) OR (cond3)
    """
    if not constraints:
        return query

    or_clauses = []

    for and_group in constraints:
        and_clauses = []
        for condition in and_group:
            clause = _build_clause(model, condition)
            if clause is not None:
                and_clauses.append(clause)

        if and_clauses:
            or_clauses.append(and_(*and_clauses))

    if not or_clauses:
        return query

    return query.filter(or_(*or_clauses))


def _build_clause(model, condition: dict):
    """
    Buduje pojedynczą klauzulę SQLAlchemy, identyfikując kolumnę i rzutując wartość.
    """
    left = condition['left']
    right = condition['right']
    op = condition['op']

    # Identyfikacja która strona to kolumna (resource.*) a która to wartość
    column_path = None
    value = None

    if str(left).startswith("resource."):
        column_path = left
        value = right
    elif str(right).startswith("resource."):
        column_path = right
        value = left
        # Jeśli zamieniliśmy strony, musimy odwrócić operatory nierówności
        if op in [">", "<", ">=", "<="]:
            op_map = {">": "<", "<": ">", ">=": "<=", "<=": ">="}
            op = op_map[op]
    else:
        # Warunek nie dotyczy zasobu
        return None

    # Pobranie obiektu kolumny z modelu
    col_name = column_path.split(".")[1]
    column = getattr(model, col_name, None)

    if column is None:
        logger.warning(f"Model {model.__name__} nie posiada kolumny {col_name}")
        return None

    # Mapowanie operatora na SQLAlchemy
    operators = {
        "==": lambda c, v: c == v,
        "!=": lambda c, v: c != v,
        ">": lambda c, v: c > v,
        "<": lambda c, v: c < v,
        ">=": lambda c, v: c >= v,
        "<=": lambda c, v: c <= v,
    }

    return operators[op](column, value)


class SQLConstraintProvider:
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

    def __call__(self, subject_id: int = Depends(get_subject_id)) -> list:
        auth_request = {
            "subject": {"id": str(subject_id), "type": self.subject_type},
            "resource": {"type": self.resource_type},
            "action": self.action,
            "mode": Mode.CONSTRAINTS
        }

        logger.info(f"Getting constraints for {self.action} on {self.resource_type} by subject {self.subject_type}:{subject_id}")

        try:
            response = requests.post(
                PDP_URL,
                json=auth_request,
                timeout=5
            )
            response.raise_for_status()
            data = response.json()

            if data["decision"] == "DENY":
                raise HTTPException(status_code=403, detail="No access to this resource type")

            if data["decision"] == Decision.ALLOW and "constraints" not in data:
                return []

            return data.get("constraints", [])

        except Exception as e:
            logger.error(f"PDP communication error: {e}")
            raise HTTPException(status_code=500, detail="Authorization engine error")

