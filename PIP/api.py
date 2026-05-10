from typing import Annotated

import uvicorn
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from common.settings import Settings
from common.schemas import AttributeRequest, AttributeResponse, AddDelegationRequest, RevokeDelegationRequest, \
    AddDelegationResponse, RevokeDelegationResponse, DelegationSchema, GetDelegationsResponse, GetDelegationsRequest
from common.logger import get_logger
from common.registry import SchemaRegistry, SourceRegistry
from attributes_registry import AttributeRegistry
import db
import models
import delegations

logger = get_logger("PIP-SERVICE")
attribute_registry: AttributeRegistry


@asynccontextmanager
async def lifespan(app: FastAPI):
    global attribute_registry
    load_dotenv()
    # Wczytanie ścieżek
    resource_schema_path = os.getenv("RESOURCE_SCHEMA_PATH")
    attribute_source_path = os.getenv("ATTRIBUTE_SOURCE_PATH")
    settings_path = os.getenv("SETTINGS_PATH")
    # Utworzenie obiektów z konfiguracją
    settings = Settings(settings_path)
    schema_registry = SchemaRegistry(path=resource_schema_path)
    source_registry = SourceRegistry(path=attribute_source_path)
    attribute_registry = AttributeRegistry(schema_registry=schema_registry, source_registry=source_registry)
    # Inicjalizacja tabeli z delegacjami
    with db.SessionLocal() as session:
        try:
            table_name = settings.get_table_name()
            delegations.ensure_table_exists(session, table_name, db.Base.metadata)
        except Exception as e:
            logger.error(f"Error occurred when initializing delegation table: {e}")
            raise e
    yield

app = FastAPI(lifespan=lifespan)


@app.post("/delegations", response_model=AddDelegationResponse)
def add_delegation(request: AddDelegationRequest, db: Session = Depends(db.get_db)):
    delegation = DelegationSchema(**request.dict())
    result = delegations.add_delegation(db=db, data=delegation)
    if not result:
        raise HTTPException(status_code=409, detail="Similar delegation is still active")
    return AddDelegationResponse(detail="success")


@app.patch("/delegations/revoke", response_model=RevokeDelegationResponse)
def revoke_delegation(request: RevokeDelegationRequest, db: Session = Depends(db.get_db)):
    delegation = DelegationSchema(**request.dict())
    result = delegations.revoke_delegation(db=db, data=delegation)

    if not result:
        raise HTTPException(status_code=404, detail="Delegation not found")

    return RevokeDelegationResponse(detail="success")


@app.get("/delegations", response_model=GetDelegationsResponse)
def get_delegations(params: Annotated[GetDelegationsRequest, Depends()], db: Session = Depends(db.get_db)):
    logger.info(f"Received delegation retrieval request: {params}")
    result = delegations.get_delegations(db=db, data=params)
    logger.info(f"Following delegation entries found: {result}")
    return GetDelegationsResponse(delegations=result)


@app.post("/attributes", response_model=AttributeResponse)
async def get_attributes(request: AttributeRequest) -> AttributeResponse:
    logger.info(f"Received attribute request: {request}")

    attributes = await attribute_registry.get_attributes(resource_type=request.type, resource_id=request.id, attributes=request.attributes)

    logger.info(f"Sending response: {AttributeResponse(attributes=attributes)}")
    return AttributeResponse(attributes=attributes)


@app.get("/")
def health_check():
    return {"status": "alive", "service": "policy_information_point"}


if __name__ == "__main__":
    # Uruchomienie serwera
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8002
    )