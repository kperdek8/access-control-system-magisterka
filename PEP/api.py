from typing import List

import uvicorn
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from common.logger import get_logger
from common.schemas import Action
from policy_enforcer import PolicyEnforcer
from constraint_provider import SQLConstraintProvider, sql_apply_constraints
import db
import models
import schemas
import seed

models.Base.metadata.create_all(bind=db.engine)


async def lifespan(app: FastAPI):
    with db.SessionLocal() as session:
        seed.seed_users(session)
    yield

logger = get_logger("PEP-SERVICE")
logger.setLevel("DEBUG")
app = FastAPI(lifespan=lifespan)


@app.get("/users", response_model=List[schemas.UserSchema])
def get_users(database: Session = Depends(db.get_db),
              constraints: list = Depends(SQLConstraintProvider(action=Action.READ, resource_type="user", subject_type="user"))
              ):
    query = database.query(models.User)
    logger.debug(f"Base query: {query}")
    logger.debug(f"Constraints: {constraints}")
    users = sql_apply_constraints(query=query, model=models.User, constraints=constraints)
    logger.debug(f"Query updated with constraints: {users.statement.compile(compile_kwargs={"literal_binds": True})}")
    return users.all()


@app.get("/users/{resource_id}", response_model=schemas.UserSchema)
def get_user(resource_id: int,
             _ = Depends(PolicyEnforcer(action=Action.READ, resource_type="user", subject_type="user",
                                      error_msg="Musisz być właścicielem profilu")),
             database: Session = Depends(db.get_db)
             ):
    user_data = database.query(models.User).filter(models.User.id == resource_id).first()

    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    return user_data


@app.get("/")
def health_check():
    return {"status": "alive", "service": "policy_enforcement_point"}


if __name__ == "__main__":
    # Uruchomienie serwera
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000
    )
