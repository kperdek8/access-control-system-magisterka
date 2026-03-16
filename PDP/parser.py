from lark import Lark

from transformer import PolicyTransformer
from walk_tree import walk_tree

grammar = """
    ?start: (rule | delegation)+
    
    rule: "RULE" action "IF" condition
    
    // Akcja
    action: ALLOW_KW | DENY_KW
    ALLOW_KW: "ALLOW"
    DENY_KW: "DENY"
    
    // Operatory logiczne
    ?condition: or_operator
    ?or_operator: and_operator ("OR" and_operator)*
    ?and_operator: atom ("AND" atom)*
    ?atom: comparison 
        | "(" condition ")"
    comparison: attribute op value
    
    // Atrybuty
    attribute: WORD "." WORD
    op: EQUAL_OP | NOT_EQUAL_OP | GREATER_THAN_OR_EQUAL_OP | GREATER_THAN_OP | LESSER_THAN_OR_EQUAL_OP | LESSER_THAN_OP
    EQUAL_OP: "=="
    NOT_EQUAL_OP: "!="
    GREATER_THAN_OP: ">"
    GREATER_THAN_OR_EQUAL_OP: ">="
    LESSER_THAN_OP: "<"
    LESSER_THAN_OR_EQUAL_OP: "<="
  
    // Delegacja
    delegation: "DELEGATION" "{" parameter+ "}"
    parameter: key ":" value
    key: WORD
    
    // Pozostale
    value: WORD | NUMBER | ESCAPED_STRING
    WORD: /[a-zA-Z_][a-zA-Z0-9_]*/
    
    // Importy
    %import common.ESCAPED_STRING
    %import common.NUMBER
    %import common.WS
    %ignore WS
"""

parser = Lark(grammar, parser='earley')

policy_str = """
RULE ALLOW IF environment.test == TRUE OR (user.role == accountant AND object.type == invoice)
RULE ALLOW IF (environment.test == TRUE OR user.role == accountant) AND object.type == invoice
RULE ALLOW IF environment.test == TRUE OR user.role == accountant AND object.type == invoice
RULE ALLOW IF environment.test == TRUE AND user.role == accountant OR object.type == invoice
DELEGATION {
    test: true
    other_test: 15
}
"""
tree = parser.parse(policy_str)
policy = PolicyTransformer().transform(tree)
print(policy)

#walk_tree(tree)