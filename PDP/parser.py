import os

from lark import Lark
from lark.tree import pydot__tree_to_png

from transformer import PolicyTransformer
from dotenv import load_dotenv

load_dotenv("../.env")
current_dir = os.path.dirname(__file__)
grammar_path = os.path.join(current_dir, "grammar.lark")
policies_path = os.getenv("POLICY_REPOSITORY_PATH")

parser = Lark.open("grammar.lark", rel_to=__file__, start='start')


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


def load_and_parse_policies():
    policies = load_policies()
    parsed_policies = []
    for policy in policies:
        parsed_policy = parse(policy)
        for rule in parsed_policy:
            parsed_policies.append(rule)
    return parsed_policies
