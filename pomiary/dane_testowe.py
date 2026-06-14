import random
import json

# Słowniki i dane pomocnicze
RESOURCE_TYPES = ["user", "dokument_finansowy", "raport_projektowy", "faktura", "kod_zrodlowy"]
ROLES = ["manager", "employee", "admin", "auditor"]
DEPARTMENTS = ["finanse", "it", "hr", "marketing", "zarzad"]
ACTIONS = ["READ", "WRITE", "DELETE"]
CLASSIFICATIONS = ["PUBLIC", "INTERNAL", "CONFIDENTIAL"]

# Mapowanie atrybutów dla każdego typu (zgodnie ze schema.yaml)
SCHEMA_MAP = {
    "user": {
        "table": "users",
        "attrs": {
            "id": "id",
            "first_name": "first_name",
            "surname": "surname",
            "role": "role",
            "department": "dept",
            "salary": "salary"
        }
    },
    "dokument_finansowy": {
        "table": "financial_docs",
        "attrs": {"id": "id", "title": "title", "department": "dept", "classification": "class_level",
                  "total_amount": "total_amount"}
    },
    "raport_projektowy": {
        "table": "project_reports",
        "attrs": {"id": "id", "project_name": "proj_name", "department": "dept", "classification": "class_level",
                  "is_active": "active_flag"}
    },
    "faktura": {
        "table": "invoices",
        "attrs": {"id": "id", "invoice_number": "inv_num", "department": "dept", "classification": "class_level",
                  "contractor_id": "client_id"}
    },
    "kod_zrodlowy": {
        "table": "source_codes",
        "attrs": {"id": "id", "repository": "repo_name", "department": "dept", "classification": "class_level",
                  "required_level": "req_clearance"}
    }
}

# Definicje generatorów losowych wartości dla konkretnych atrybutów
SUBJECT_ATTRS = {
    "subject.id": lambda: str(random.choice([i for i in range(2, 100) if i != 50])),  # Losuje ID omijając 1, 50 i 100
    "subject.role": lambda: f'"{random.choice(ROLES)}"',
    "subject.department": lambda: f'"{random.choice(DEPARTMENTS)}"',
    "subject.salary": lambda: str(random.randint(4000, 18000))
}

RESOURCE_ATTRS = {
    "user": {
        "resource.id": lambda: str(random.choice([i for i in range(2, 100) if i != 50])),
        "resource.role": lambda: f'"{random.choice(ROLES)}"',
        "resource.department": lambda: f'"{random.choice(DEPARTMENTS)}"',
        "resource.salary": lambda: str(random.randint(4000, 18000))
    },
    "dokument_finansowy": {
        "resource.id": lambda: str(random.randint(1, 100)),
        "resource.department": lambda: f'"{random.choice(DEPARTMENTS)}"',
        "resource.classification": lambda: f'"{random.choice(CLASSIFICATIONS)}"',
        "resource.total_amount": lambda: str(random.randint(1000, 100000))
    },
    "raport_projektowy": {
        "resource.id": lambda: str(random.randint(1, 100)),
        "resource.department": lambda: f'"{random.choice(DEPARTMENTS)}"',
        "resource.classification": lambda: f'"{random.choice(CLASSIFICATIONS)}"',
        "resource.is_active": lambda: f'"{random.choice(["true", "false"])}"'
    },
    "faktura": {
        "resource.id": lambda: str(random.randint(1, 100)),
        "resource.department": lambda: f'"{random.choice(DEPARTMENTS)}"',
        "resource.classification": lambda: f'"{random.choice(CLASSIFICATIONS)}"',
        "resource.contractor_id": lambda: str(random.randint(500, 999))
    },
    "kod_zrodlowy": {
        "resource.id": lambda: str(random.randint(1, 100)),
        "resource.department": lambda: f'"{random.choice(DEPARTMENTS)}"',
        "resource.classification": lambda: f'"{random.choice(CLASSIFICATIONS)}"',
        "resource.required_level": lambda: str(random.randint(1, 5))
    }
}


def get_random_comparison(res_type):
    if random.random() > 0.5:
        attr = random.choice(list(SUBJECT_ATTRS.keys()))
        attr_type = "num" if "salary" in attr or "id" in attr else "str"
    else:
        attr = random.choice(list(RESOURCE_ATTRS[res_type].keys()))
        attr_type = "num" if "total_amount" in attr or "id" in attr or "required_level" in attr or "contractor_id" in attr else "str"

    if attr_type == "num":
        op = random.choice(["==", "!=", ">", ">=", "<", "<="])
    else:
        op = random.choice(["==", "!="])

    if random.random() < 0.15 and "department" in attr:
        return f"{attr} {op} resource.department" if "subject" in attr else f"subject.department {op} {attr}"
    if random.random() < 0.15 and "id" in attr:
        return f"{attr} {op} resource.id" if "subject" in attr else f"subject.id {op} {attr}"

    if "subject" in attr:
        val = SUBJECT_ATTRS[attr]()
    else:
        val = RESOURCE_ATTRS[res_type][attr]()

    return f"{attr} {op} {val}"


def generate_random_condition(res_type):
    complexity = random.choice(["simple", "and", "or", "complex"])
    comp1 = get_random_comparison(res_type)
    comp2 = get_random_comparison(res_type)
    comp3 = get_random_comparison(res_type)

    if complexity == "simple":
        return comp1
    elif complexity == "and":
        return f"{comp1} AND {comp2}"
    elif complexity == "or":
        return f"{comp1} OR {comp2}"
    else:
        return f"{comp1} AND ({comp2} OR {comp3})"


dsl_output = []
yaml_output = ["types:"]

# 1. GENEROWANIE PLIKU schema.yaml
for r_type, info in SCHEMA_MAP.items():
    yaml_output.append(f"  {r_type}:")
    yaml_output.append(f'    source: "main_db"')
    yaml_output.append(f'    table: "{info["table"]}"')
    yaml_output.append(f'    primary_key: "id"')
    yaml_output.append(f"    attributes:")
    for attr_name, col_name in info["attrs"].items():
        yaml_output.append(f'      {attr_name}: "{col_name}"')


# Pomocnik budujący precyzyjne reguły testowe dla zasobu 'user'
def make_benchmark_rule(target_id):
    res_type = "user"
    action = "READ"
    condition = generate_random_condition(res_type)

    # Wymuszenie dopasowania reguły tylko dla target_id
    full_cond = f"({condition} AND subject.id == {target_id}) OR (subject.id == {target_id})"

    return (
        f'RULE ALLOW IF context.action == "{action}" '
        f'AND resource.type == "{res_type}" '
        f'AND subject.type == "user" '
        f'AND ({full_cond})'
    )


# 2. GENEROWANIE PLIKU DSL (997 reguł szumu + 3 punkty kontrolne = 1000 reguł dostępu)
dsl_output.append("# AUTOGENEROWANE UNIWERSALNE REGUŁY DOSTĘPOWE (1000)")

# Generowanie 997 losowych reguł tła z filtrami wykluczającymi ID testowe (1, 50, 100)
background_noise = []
for _ in range(997):
    res_type = random.choice(RESOURCE_TYPES)
    action = random.choice(ACTIONS)
    decision = "ALLOW" if random.random() > 0.2 else "DENY"
    condition = generate_random_condition(res_type)

    # Gwarantujemy, że ta reguła NIE dotyczy użytkowników o ID 1, 50 oraz 100
    full_rule = (
        f'RULE {decision} IF context.action == "{action}" '
        f'AND resource.type == "{res_type}" '
        f'AND subject.type == "user" '
        f'AND (({condition}) AND subject.id != 1 AND subject.id != 50 AND subject.id != 100)'
    )
    background_noise.append(full_rule)

# Budujemy strukturę pliku (1. reguła -> szum -> 49. reguła -> szum -> 100. reguła)
access_rules = []

# Pozycja 1: Punkt kontrolny dla BEST_CASE (id == 1 przechodzi od razu)
access_rules.append(make_benchmark_rule(target_id=1))

# Pozycje 2-499: Pierwsza paczka szumu (498 reguł)
access_rules.extend(background_noise[:498])

# Pozycja 500: Środkowy punkt kontrolny dla AVERAGE_CASE (id == 50 przechodzi w połowie pliku)
access_rules.append(make_benchmark_rule(target_id=50))

# Pozycje 501-999: Druga paczka szumu (499 reguł)
access_rules.extend(background_noise[498:])

# Pozycja 1000: Punkt kontrolny dla WORST_CASE (id == 100 przeczesuje cały plik)
access_rules.append(make_benchmark_rule(target_id=100))

for idx, rule_text in enumerate(access_rules, 1):
    dsl_output.append(f"# Reguła dostępowa nr {idx}\n{rule_text}\n")

dsl_output.append("# AUTOGENEROWANE REGUŁY DELEGACJI (20)")

for i in range(1, 21):
    res_type = random.choice(RESOURCE_TYPES)
    if res_type == "user":
        rule_cond = 'delegator.id == resource.id OR delegator.role == "manager"'
    else:
        rule_cond = f'delegator.department == resource.department AND delegator.role == "manager"'

    delegation_block = f"""DELEGATION {{
    rule: {rule_cond}
    resource_type: "{res_type}"
    delegator_type: "user"
    delegatee_type: "user"
    actions: ["{random.choice(ACTIONS)}"]
    active: "true"
    max_duration: P{random.randint(1, 14)}D
    max_depth: {random.randint(1, 3)}
}}"""
    dsl_output.append(f"# Reguła delegacji nr {i}\n{delegation_block}\n")

with open("schema.yaml", "w", encoding="utf-8") as f:
    f.write("\n".join(yaml_output))

with open("polityki.policy", "w", encoding="utf-8") as f:
    f.write("\n".join(dsl_output))

print("Wygenerowano polityki.policy oraz schema.yaml.")