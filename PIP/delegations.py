import datetime
from operator import and_

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy import inspect, Table
from common.logger import get_logger
from common.schemas import DelegationSchema, GetDelegationsRequest
from models import Delegation

logger = get_logger("PEP_SERVICE")


def ensure_table_exists(session: Session, table_name: str, metadata):
    """
    Sprawdza czy tabela istnieje w bazie danych.
    Jeżeli nie, tworzy ją na podstawie dostarczonych metadanych.
    """
    engine = session.get_bind()
    inspector = inspect(engine)

    existing_tables = inspector.get_table_names()

    if table_name not in existing_tables:
        logger.info(f"Table {table_name} does not exists. Creating...")
        try:
            target_table = metadata.tables[table_name]
            target_table.create(engine)
            logger.info(f"Table {table_name} created.")
        except KeyError:
            logger.error(f"Error: Table '{table_name}' not defined in Base.metadata!")
    else:
        logger.info(f"Table '{table_name}' found in database.")


def add_delegation(db: Session, data: DelegationSchema):
    now = datetime.datetime.now()

    existing_delegation = db.query(Delegation).filter(
        Delegation.delegator_id == data.delegator_id,
        Delegation.delegator_type == data.delegator_type,
        Delegation.delegatee_id == data.delegatee_id,
        Delegation.delegatee_type == data.delegatee_type,
        Delegation.resource_id == data.resource_id,
        Delegation.resource_type == data.resource_type,
        Delegation.active == True
    ).first()

    print(existing_delegation)

    if existing_delegation:
        expiration_date = existing_delegation.start_date + existing_delegation.duration
        if expiration_date > now:
            # Delegacja nadal trwa - blokujemy dodanie nowej
            return None
        else:
            # Delegacja wygasła czasowo, zaktualizowanie statusu "active"
            existing_delegation.is_active = False
            db.commit()

    try:
        new_delegation = Delegation(**data.model_dump())
        db.add(new_delegation)
        db.commit()
        db.refresh(new_delegation)
        return new_delegation

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Error when adding delegation: {e}")
        raise e


def revoke_delegation(db: Session, data: DelegationSchema):
    delegation = db.query(Delegation).filter(
        Delegation.delegator_id == data.delegator_id,
        Delegation.delegator_type == data.delegator_type,
        Delegation.delegatee_id == data.delegatee_id,
        Delegation.delegatee_type == data.delegatee_type,
        Delegation.resource_id == data.resource_id,
        Delegation.resource_type == data.resource_type,
        Delegation.active == True
    ).first()

    if not delegation:
        return None

    try:
        delegation.active = False
        db.commit()
        db.refresh(delegation)
        return delegation
    except Exception:
        db.rollback()
        raise


def get_delegations(db: Session, data: GetDelegationsRequest):
    now = datetime.datetime.now()

    query_results = db.query(Delegation).filter(
        Delegation.delegatee_id == data.subject_id,
        Delegation.delegatee_type == data.subject_type,
        Delegation.resource_id == data.resource_id,
        Delegation.resource_type == data.resource_type,
        Delegation.active == True
    ).all()

    valid_delegations = [
        d for d in query_results
        if (d.start_date + d.duration) > now
    ]

    return valid_delegations
