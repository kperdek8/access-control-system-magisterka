from sqlalchemy import Column, Integer, String, DateTime, Boolean
from datetime import datetime
from db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String)
    surname = Column(String)
    role = Column(String)
    dept = Column(String)
    salary = Column(Integer)


class FinancialDoc(Base):
    __tablename__ = "financial_docs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    dept = Column(String)
    class_level = Column(String)
    total_amount = Column(Integer)


class ProjectReport(Base):
    __tablename__ = "project_reports"

    id = Column(Integer, primary_key=True, index=True)
    proj_name = Column(String)
    dept = Column(String)
    class_level = Column(String)
    is_active = Column(Boolean)


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    inv_num = Column(String)
    dept = Column(String)
    class_level = Column(String)
    client_id = Column(Integer)


class SourceCode(Base):
    __tablename__ = "source_codes"

    id = Column(Integer, primary_key=True, index=True)
    repo_name = Column(String)
    dept = Column(String)
    class_level = Column(String)
    req_clearance = Column(Integer)