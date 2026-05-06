import uuid

from sqlalchemy import Column, String, DateTime, Interval, JSON, Boolean
from db import Base, settings


class Delegation(Base):
    __tablename__ = settings.get_table_name()

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    action = Column(JSON, nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    delegator_id = Column(String, nullable=False)
    delegator_type = Column(String, nullable=False)
    delegatee_id = Column(String, nullable=False)
    delegatee_type = Column(String, nullable=False)
    duration = Column(Interval, nullable=False)
    resource_id = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    start_date = Column(DateTime, nullable=False)