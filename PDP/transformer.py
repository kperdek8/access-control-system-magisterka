from lark import Transformer, Token
from common.logger import get_logger
import operator

logger = get_logger("PDP-SERVICE")
# logger.setLevel("DEBUG")


class Attribute:
    def __init__(self, category, attribute):
        self.category = category
        self.attribute = attribute

    def __str__(self):
        return f"{self.category}.{self.attribute}"

    __repr__ = __str__

    def collect_attributes(self):
        return {(str(self.category), str(self.attribute))}

    def evaluate(self, context: dict):
        category = context.get(self.category, {})
        return category.get(self.attribute)


class Comparison:
    OPERATORS = {
        "==": operator.eq,
        "!=": operator.ne,
        ">": operator.gt,
        ">=": operator.ge,
        "<": operator.lt,
        "<=": operator.le,
    }

    def __init__(self, left, op, right):
        self.left = left
        self.op = op.upper()
        self.right = right

    def __str__(self):
        return f"{self.left} {self.op} {self.right}"

    __repr__ = __str__

    def collect_attributes(self):
        attrs = set()
        if isinstance(self.left, Attribute):
            attrs.update(self.left.collect_attributes())
        if isinstance(self.right, Attribute):
            attrs.update(self.right.collect_attributes())
        return attrs

    def evaluate(self, context: dict):
        # Pobranie wartości z kontekstu jeżeli strona porównania jest atrybutem, w przeciwnym wypadku odczytanie stałej wartości
        logger.debug(f"Evaluating comparison: {self.left} {self.op} {self.right}")
        left_val = self.left.evaluate(context) if hasattr(self.left, 'evaluate') else self.left
        right_val = self.right.evaluate(context) if hasattr(self.right, 'evaluate') else self.right
        logger.debug(f"Evaluated left value: {left_val}")
        logger.debug(f"Evaluated right value: {right_val}")

        if left_val is None or right_val is None:
            return False

        op_func = self.OPERATORS.get(self.op)

        if not op_func:
            raise ValueError(f"Unsupported operator: '{self.op}'")

        try:
            return op_func(left_val, right_val)
        except TypeError:
            raise TypeError(f"Unsupported operation: '{left_val} {self.op} {right_val}'")


class LogicalOperator:
    def __init__(self, left, op, right):
        self.left = left
        self.op = op.upper()
        self.right = right

    def __str__(self):
        return f"({self.left} {self.op} {self.right})"

    __repr__ = __str__

    def collect_attributes(self):
        return self.left.collect_attributes().union(self.right.collect_attributes())

    def evaluate(self, context: dict):
        logger.debug(f"Evaluating logical operation: {self.left} {self.op} {self.right}")
        left_res = self.left.evaluate(context)
        logger.debug(f"Evaluated left expression: {left_res}")

        if self.op == "OR" and left_res is True:
            return True
        if self.op == "AND" and left_res is False:
            return False

        right_res = self.right.evaluate(context)
        logger.debug(f"Evaluated right expression: {right_res}")

        if self.op == "OR":
            return left_res or right_res
        if self.op == "AND":
            return left_res and right_res

        return False


class Rule:
    def __init__(self, type, action, conditions):
        self.type = type
        self.action = action
        self.conditions = conditions

    def collect_attributes(self):
        if self.conditions:
            return self.conditions.collect_attributes()
        return set()

    def evaluate(self, context: dict):
        logger.debug(f"Evaluating conditions: {self.conditions}")
        is_triggered = self.conditions.evaluate(context)

        if is_triggered:
            logger.debug(f"Decision {self.action}")
            return self.action

        logger.debug(f"Decision NOT APPLICABLE")
        return "NOT_APPLICABLE"


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
        return Rule(type="RULE", action=action, conditions=conditions)

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
        return Attribute(category=children[0], attribute=children[1])

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