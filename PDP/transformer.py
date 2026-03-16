from lark import Transformer, Token


class Comparison:
    def __init__(self, left, op, right):
        self.left = left
        self.op = op.upper()
        self.right = right

    def __str__(self):
        return f"{self.left} {self.op} {self.right}"

    __repr__ = __str__


class LogicalOperator:
    def __init__(self, left, op, right):
        self.left = left
        self.op = op.upper()
        self.right = right

    def __str__(self):
        return f"({self.left} {self.op} {self.right})"

    __repr__ = __str__


class PolicyTransformer(Transformer):
    #  Obsługa Delegacji
    def delegation(self, children):
        return {"type": "DELEGATION", "params": dict(children)}

    def parameter(self, children):
        key, value = children
        return str(key), value

    def key(self, children):
        return str(children[0])

    # Obsługa Reguł
    def rule(self, children):
        action, conditions = children
        return {
            "type": "RULE",
            "action": action,
            "conditions": conditions
        }

    def action(self, children):
        return str(children[0])

    # Operatory logiczne
    def or_operator(self, children):
        return LogicalOperator(left=children[0], op="OR", right=children[1])

    def and_operator(self, children):
        return LogicalOperator(left=children[0], op="AND", right=children[1])

    def comparison(self, children):
        return Comparison(left=children[0], op=children[1], right=children[2])

    def attribute(self, children):
        return f"{children[0]}.{children[1]}"

    def op(self, children):
        return str(children[0])

    def value(self, children):
        val = children[0]
        # Konwersja typów
        if isinstance(val, Token):
            if val.type == 'NUMBER': return float(val)
            if val.type == 'ESCAPED_STRING': return val[1:-1]
        return str(val)

    def start(self, children):
        return children