from typing import List
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
import db
import models
import schemas
import seed

app = FastAPI()

models.Base.metadata.create_all(bind=db.engine)


@app.on_event("startup")
def configure_db():
    # Inicjalizacja danych przy starcie aplikacji
    with db.SessionLocal() as session:
        seed.seed_users(session)


@app.get("/users", response_model=List[schemas.UserSchema])
def get_users(database: Session = Depends(db.get_db)):
    users = database.query(models.User).all()
    return users


@app.get("/users/{id}", response_model=schemas.UserSchema)
def get_user(id: int, database: Session = Depends(db.get_db)):
    user = database.query(models.User).filter(models.User.id == id).first()
    return user or {"error": "User not found"}


@app.get("/")
def health_check():
    return {"status": "alive", "service": "policy_enforcement_point"}
