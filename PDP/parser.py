import os
from collections import defaultdict

from lark import Lark
from lark.tree import pydot__tree_to_png

from common.registry import SchemaRegistry
from transformer import PolicyTransformer, DelegationRule, Rule
from dotenv import load_dotenv

load_dotenv("../.env")
current_dir = os.path.dirname(__file__)
grammar_path = os.path.join(current_dir, "grammar.lark")
policies_path = os.getenv("POLICY_REPOSITORY_PATH")

parser = Lark.open("grammar.lark", rel_to=__file__, start='start')


class PolicyStore:
    def __init__(self, all_rules, schema_registry: SchemaRegistry):
        # Główny indeks
        # [res_type][del_type][sub_type][action]
        self.delegations = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list[DelegationRule]))))

        # Indeks pomocniczy
        # Pozwala pominąć delegatora (np. w żądaniu o dostęp przed pobraniem istotnych delegacji z PIP).
        # [res_type][sub_type][action]
        self.delegations_by_delegatee = defaultdict(lambda: defaultdict(lambda: defaultdict(list[DelegationRule])))

        self.rules = []

        for rule in all_rules:
            if isinstance(rule, DelegationRule):
                if hasattr(rule, 'active') and not rule.active:
                    continue
                # Walidacja typów podmiotów z rejestrem schematów.
                types_to_check = {
                    "resource": rule.resource_type,
                    "delegatee": rule.delegatee_type,
                    "delegator": rule.delegator_type
                }
                for category, type in types_to_check.items():
                    if not schema_registry.get_mapping(type):
                        raise RuntimeError(f"Rule references unknown {category}_type: '{type}'")
                for action in rule.actions:
                    self.delegations[rule.resource_type][rule.delegatee_type][rule.delegator_type][action].append(
                        rule)
                    self.delegations_by_delegatee[rule.resource_type][rule.delegatee_type][action].append(rule)
            elif isinstance(rule, Rule):
                self.rules.append(rule)

    # Wyszukanie delegacji z konkretnym delegatorem (tworzenie delegacji lub weryfikacja ważności przyznanych delegacji)
    def find_delegation(self, res_type, delegatee_type, delegator_type, action):
        return self.delegations.get(res_type, {}).get(delegatee_type, {}).get(delegator_type, {}).get(action, [])

    # Wyszukanie delegacji z pominięciem delegatora (sprawdzenie czy istnieje możliwość dostępu przez delegowane uprawnienia)
    def find_delegation_by_delegatee(self, res_type, delegatee_type, action):
        return self.delegations_by_delegatee.get(res_type, {}).get(delegatee_type, {}).get(action, [])


def load_policies():
    if not os.path.exists(policies_path):
        print(f"Folder {policies_path} nie istnieje")
        return []

    policy_files = [file for file in os.listdir(policies_path) if os.path.splitext(file)[1] == '.policy']
    policies = []
    for policy_file in policy_files:
        with open(os.path.join(policies_path, policy_file), "r") as f:
            policies.append(f.read())
    return policies


def parse(policy):
    tree = parser.parse(policy)
    #pydot__tree_to_png(tree, "tree.png")
    policy = PolicyTransformer().transform(tree)
    return policy


def load_and_parse_policies(schema_registry: SchemaRegistry):
    policies = load_policies()
    parsed_policies = []
    for policy in policies:
        parsed_policy = parse(policy)
        for rule in parsed_policy:
            parsed_policies.append(rule)
    return PolicyStore(parsed_policies, schema_registry)
