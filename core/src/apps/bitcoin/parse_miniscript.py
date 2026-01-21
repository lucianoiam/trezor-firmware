try:
    from typing import List, Optional
except ImportError:
    pass

SEMANTIC_OPERATOR = 0
SEMANTIC_OPERAND = 1

ALNUM = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

# This parser accepts output descriptors containing miniscript (e.g. wsh(...), sh(...)).
# Descriptor wrappers are parsed but discarded during normalization, as only the
# miniscript content is relevant for spending path analysis and script encoding.


def isalnum(c: str) -> bool:
    return c in ALNUM


class MiniscriptNode:
    """Node representing a miniscript fragment, preserving type modifiers."""

    def __init__(
        self,
        value: str,
        sem_type: int,
        children: Optional[List["MiniscriptNode"]] = None,
    ) -> None:
        self.value = value
        self.sem_type = sem_type
        self.children: List["MiniscriptNode"] = children if children else []

    @property
    def normalized_value(self) -> str:
        """Return policy-normalized value (strips type modifiers)."""
        val = self.value
        # Strip prefix wrappers (a:, s:, c:, d:, v:, j:, n:, l:, u:, t:)
        while len(val) >= 2 and val[1] == ":" and val[0] in "ascdvjnlut":
            val = val[2:]
        # Normalize operator names: or_d -> or, and_v -> and, etc.
        if val.startswith("or_"):
            return "or"
        if val.startswith("and_"):
            return "and"
        # Normalize key types: pk_k, pk_h, pkh -> pk
        if val in ("pk_k", "pk_h", "pkh"):
            return "pk"
        # Skip descriptor wrappers
        if val in ("wsh", "sh"):
            return ""
        return val


def tokenize(text: str) -> List[str]:
    tokens: List[str] = []
    i = 0
    while i < len(text):
        c = text[i]
        if c in " \t\n\r":
            i += 1
        elif c in "(),":
            tokens.append(c)
            i += 1
        elif isalnum(c) or c in "*/<>;:$_@":
            start = i
            while i < len(text) and (isalnum(text[i]) or text[i] in "*/<>;:$_@"):
                i += 1
            tokens.append(text[start:i])
        else:
            i += 1
    return tokens


def parse_miniscript(text: str) -> MiniscriptNode:
    """Parse miniscript text into a MiniscriptNode tree."""
    tokens = tokenize(text)
    pos = 0
    stack: List[MiniscriptNode] = []
    root: Optional[MiniscriptNode] = None

    while pos < len(tokens):
        token = tokens[pos]
        pos += 1

        if token == ",":
            continue
        elif token == ")":
            if len(stack) > 1:
                stack.pop()
            elif len(stack) == 1:
                root = stack.pop()
            continue

        if pos < len(tokens) and tokens[pos] == "(":
            node = MiniscriptNode(token, SEMANTIC_OPERATOR)
            pos += 1
        else:
            node = MiniscriptNode(token, SEMANTIC_OPERAND)

        if len(stack) > 0:
            parent = stack[len(stack) - 1]
            parent.children.append(node)

        if node.sem_type == SEMANTIC_OPERATOR:
            stack.append(node)
        elif root is None and len(stack) == 0:
            root = node

    if root is None and len(stack) > 0:
        root = stack[0]

    if root is None:
        raise ValueError("Failed to parse miniscript")

    return root
