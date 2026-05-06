from sqlalchemy.orm import Session
from models import User


def seed_users(db: Session):
    if db.query(User).count() == 0:
        print("Seeding database with initial users...")
        sample_users = [
            User(first_name="adam", surname="kowalski", role="admin", department="IT", salary=12000),
            User(first_name="anna", surname="nowak", role="manager", department="HR", salary=10000),
            User(first_name="jan", surname="lewandowski", role="worker", department="Production", salary=6000)
        ]
        db.add_all(sample_users)
        db.commit()
    else:
        print("Database already has data, skipping seed.")