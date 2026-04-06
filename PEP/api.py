from typing import List
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from auth_client import verify_authorization
import db
import models
import schemas
import seed
from common.schemas import Action

app = FastAPI()
security = HTTPBearer()

models.Base.metadata.create_all(bind=db.engine)


def get_user_id(res: HTTPAuthorizationCredentials = Depends(security)) -> int:
    """
    Wyciąga token z nagłówka 'Authorization: Bearer <id>' i zamienia go na id
    """
    try:
        # res.credentials to treść po słowie 'Bearer '
        user_id = int(res.credentials)
        return user_id
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format. Expected integer ID.",
            headers={"WWW-Authenticate": "Bearer"},
        )


@app.on_event("startup")
def configure_db():
    # Inicjalizacja danych przy starcie aplikacji
    with db.SessionLocal() as session:
        seed.seed_users(session)


@app.get("/users", response_model=List[schemas.UserSchema])
def get_users(database: Session = Depends(db.get_db)) -> List[schemas.UserSchema]:
    users = database.query(models.User).all()
    return users


@app.get("/users/{resource_id}", response_model=schemas.UserSchema)
def get_user(resource_id: int,
             subject_id: int = Depends(get_user_id),
             database: Session = Depends(db.get_db)
             ):
    if verify_authorization(subject={"id": subject_id, "type": "user"}, resource={"id": resource_id, "type": "user"}, action=Action.READ):
        user_data = database.query(models.User).filter(models.User.id == resource_id).first()

        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")

        return user_data
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access Denied")


@app.get("/")
def health_check():
    return {"status": "alive", "service": "policy_enforcement_point"}
