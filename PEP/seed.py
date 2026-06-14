import random
from sqlalchemy.orm import Session
from models import User, FinancialDoc, ProjectReport, Invoice, SourceCode

# Słowniki do losowania danych testowych
ROLES = ["manager", "employee", "admin", "auditor"]
DEPARTMENTS = ["finanse", "it", "hr", "marketing", "zarzad"]
CLASSIFICATIONS = ["PUBLIC", "INTERNAL", "CONFIDENTIAL"]
NAMES = ["Jan", "Anna", "Piotr", "Maria", "Krzysztof", "Katarzyna", "Tomasz", "Małgorzata"]
SURNAMES = ["Kowalski", "Nowak", "Wiśniewski", "Wójcik", "Kamiński", "Lewandowski", "Zieliński"]


def seed_all_data(db: Session):
    # 1. SEEDOWANIE UŻYTKOWNIKÓW
    if db.query(User).count() == 0:
        print("Seeding database with 100 test users...")
        users = []
        for i in range(1, 101):
            users.append(User(
                id=i,
                first_name=random.choice(NAMES),
                surname=random.choice(SURNAMES),
                role=random.choice(ROLES),
                dept=random.choice(DEPARTMENTS),
                salary=random.randint(4000, 18000)
            ))
        db.add_all(users)
        db.flush()  # flush synchronizuje ID w pamięci przed commitem
    else:
        print("Users table already has data, skipping.")

    # 2. SEEDOWANIE DOKUMENTÓW FINANSOWYCH
    if db.query(FinancialDoc).count() == 0:
        print("Seeding database with 100 financial documents...")
        docs = []
        for i in range(1, 101):
            docs.append(FinancialDoc(
                id=i,
                title=f"Dokument Finansowy {i}",
                dept=random.choice(DEPARTMENTS),
                class_level=random.choice(CLASSIFICATIONS),
                total_amount=random.randint(1000, 100000)
            ))
        db.add_all(docs)

    # 3. SEEDOWANIE RAPORTÓW PROJEKTOWYCH
    if db.query(ProjectReport).count() == 0:
        print("Seeding database with 100 project reports...")
        reports = []
        for i in range(1, 101):
            reports.append(ProjectReport(
                id=i,
                proj_name=f"Projekt {i}",
                dept=random.choice(DEPARTMENTS),
                class_level=random.choice(CLASSIFICATIONS),
                is_active=random.choice([True, False])
            ))
        db.add_all(reports)

    # 4. SEEDOWANIE FAKTUR
    if db.query(Invoice).count() == 0:
        print("Seeding database with 100 invoices...")
        invoices = []
        for i in range(1, 101):
            invoices.append(Invoice(
                id=i,
                inv_num=f"FV/{i}/2026",
                dept=random.choice(DEPARTMENTS),
                class_level=random.choice(CLASSIFICATIONS),
                client_id=random.randint(500, 999)
            ))
        db.add_all(invoices)

    # 5. SEEDOWANIE KODÓW ŹRÓDŁOWYCH
    if db.query(SourceCode).count() == 0:
        print("Seeding database with 100 source code repos...")
        repos = []
        for i in range(1, 101):
            repos.append(SourceCode(
                id=i,
                repo_name=f"repo-core-{i}",
                dept=random.choice(DEPARTMENTS),
                class_level=random.choice(CLASSIFICATIONS),
                req_clearance=random.randint(1, 5)
            ))
        db.add_all(repos)

    db.commit()
    print("Database seeding completed successfully!")