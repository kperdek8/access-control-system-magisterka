from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime
from db import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    surname = Column(String, nullable=False)
    role = Column(String)
    department = Column(String)
    salary = Column(Integer)