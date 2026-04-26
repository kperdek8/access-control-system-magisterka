import uvicorn
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
from repository_placeholder import users
from common.schemas import AttributeRequest, AttributeResponse
from common.logger import get_logger
from common.registry import SchemaRegistry, SourceRegistry
from attributes_registry import AttributeRegistry


logger = get_logger("PIP-SERVICE")
attribute_registry: AttributeRegistry


@asynccontextmanager
async def lifespan(app: FastAPI):
    global attribute_registry
    load_dotenv()
    resource_schema_path = os.getenv("RESOURCE_SCHEMA_PATH")
    attribute_source_path = os.getenv("ATTRIBUTE_SOURCE_PATH")
    schema_registry = SchemaRegistry(path=resource_schema_path)
    source_registry = SourceRegistry(path=attribute_source_path)
    attribute_registry = AttributeRegistry(schema_registry=schema_registry, source_registry=source_registry)
    yield

app = FastAPI(lifespan=lifespan)


@app.post("/attributes", response_model=AttributeResponse)
async def evaluate_decision(request: AttributeRequest) -> AttributeResponse:
    logger.info(f"Received attribute request: {request}")

    attributes = await attribute_registry.get_attributes(resource_type=request.type, resource_id=request.id, attributes=request.attributes)
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