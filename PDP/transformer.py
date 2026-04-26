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

    def collect_constraints(self, context: dict):
        val = self.evaluate(context)
        if val is not None:
            return val
        return self


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

    def collect_constraints(self, context: dict):
        left_res = self.left.collect_constraints(context) if hasattr(self.left, 'collect_constraints') else self.left
        right_res = self.right.collect_constraints(context) if hasattr(self.right,
                                                                       'collect_constraints') else self.right
        # Jeśli obie strony są już konkretnymi wartościami (nie obiektami klasy Attribute/Comparison)
        if not hasattr(left_res, 'evaluate') and not hasattr(right_res, 'evaluate'):
            logger.debug(f"Simplifying: {left_res} {self.op} {right_res} to {self.OPERATORS[self.op](left_res, right_res)}")
            return self.OPERATORS[self.op](left_res, right_res)

        # Jeśli chociaż jedna strona pozostaje atrybutem, zwracamy nowy obiekt Comparison z częściowo uzupełnionymi danymi
        return Comparison(left_res, self.op, right_res)


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

    def collect_constraints(self, context: dict):
        left_res = self.left.collect_constraints(context)
        right_res = self.right.collect_constraints(context)

        if self.op == "OR":
            if left_res is True or right_res is True:
                return True
            if left_res is False:
                return right_res
            if right_res is False:
                return left_res

        if self.op == "AND":
            if left_res is False or right_res is False:
                return False
            if left_res is True:
                return right_res
            if right_res is True:
                return left_res

        # Jeśli nic nie dało się uprościć do True/False, zwracamy uproszczony operator
        return LogicalOperator(left_res, self.op, right_res)


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

    def collect_constraints(self, context: dict):
        result = self.conditions.collect_constraints(context)

        if result is True:
            return self.action, None
        elif result is False:
            return "NOT_APPLICABLE", None
        else:
            return self.action, flatten_constraints(result)


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
        if len(children) == 1:
            return children[0]

        res = children[0]
        for next_child in children[1:]:
            res = LogicalOperator(left=res, op="OR", right=next_child)
        return res

    def and_operator(self, children):
        if len(children) == 1:
            return children[0]

        res = children[0]
        for next_child in children[1:]:
            res = LogicalOperator(left=res, op="AND", right=next_child)
        return res

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
            if val.type == 'NUMBER':
                val = float(val)
                return int(val) if val.is_integer() else val
            if val.type == 'ESCAPED_STRING': return val[1:-1]
        return str(val)

    def start(self, children):
        return children


# == FUNKCJE POMOCNICZE ==
def flatten_constraints(constraint):
    """
    Zamienia drzewo warunków na postać:
    [ [filter1, filter2], [filter3] ] -> (F1 AND F2) OR F3
    """
    if constraint is True: return [] # Brak ograniczeń (Permit All)
    if constraint is False: return None # Deny All

    # Jeśli to pojedyncze porównanie (liść drzewa)
    if isinstance(constraint, Comparison):
        return [[{
            "left": str(constraint.left),
            "op": str(constraint.op),
            "right": str(constraint.right)
        }]]

    if isinstance(constraint, LogicalOperator):
        left_flat = flatten_constraints(constraint.left)
        right_flat = flatten_constraints(constraint.right)

        if constraint.op == "OR":
            return left_flat + right_flat

        if constraint.op == "AND":
            # Iloczyn kartezjański: każdy z lewej z każdym z prawej
            # (A OR B) AND (C OR D) -> (A AND C) OR (A AND D) OR (B AND C) OR (B AND D)
            combined = []
            for l_set in left_flat:
                for r_set in right_flat:
                    combined.append(l_set + r_set)
            return combined

    return constraint