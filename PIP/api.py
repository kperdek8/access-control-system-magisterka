from fastapi import FastAPI, HTTPException
from repository_placeholder import users
from common.schemas import AttributeRequest, AttributeResponse
from common.logger import get_logger

app = FastAPI()
logger = get_logger("PIP-SERVICE")


@app.post("/attributes", response_model=AttributeResponse)
def evaluate_decision(request: AttributeRequest) -> AttributeResponse:
    logger.info(f"Received attribute request: {request}")
    user = users.get(request.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if request.type == "user":
        attributes = []
        for attribute in request.attributes:
            val = getattr(user, attribute, None)
            attributes.append({attribute: str(val)})
        return AttributeResponse(attributes=attributes)
    else:
        return AttributeResponse(attributes=[])


@app.get("/")
def health_check():
    return {"status": "alive", "service": "policy_information_point"}