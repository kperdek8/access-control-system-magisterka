import os

from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from common.settings import Settings
from dotenv import load_dotenv

load_dotenv()
settings_path = os.getenv("SETTINGS_PATH")
settings = Settings(settings_path)

url = settings.get_database_url()
engine = create_engine(settings.get_database_url())
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()