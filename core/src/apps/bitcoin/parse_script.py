try:
    from typing import List, Optional
except ImportError:
    pass

SEMANTIC_OPERATOR = 0
SEMANTIC_OPERAND = 1

ALNUM = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def isalnum(c: str) -> bool:
    return c in ALNUM


class ScriptNode:
    """Node representing a miniscript fragment, preserving type modifiers."""

    def __init__(
        self,
        value: str,
        sem_type: int,
        children: Optional[List["ScriptNode"]] = None,
    ) -> None:
        self.value = value
        self.sem_type = sem_type
        self.children: List["ScriptNode"] = children if children else []

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


def parse_script(text: str) -> ScriptNode:
    """Parse miniscript text into a ScriptNode tree."""
    tokens = tokenize(text)
    pos = 0
    stack: List[ScriptNode] = []
    root: Optional[ScriptNode] = None

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
            node = ScriptNode(token, SEMANTIC_OPERATOR)
            pos += 1
        else:
            node = ScriptNode(token, SEMANTIC_OPERAND)

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
        raise ValueError("Failed to parse script")

    return root


def get_condition_text(node: ScriptNode, xpubs: Optional[List[str]] = None) -> str:
    """Get human-readable condition for a leaf node."""
    val = node.normalized_value
    if val == "pk":
        for c in node.children:
            return "provides signature " + c.value
    elif val == "older":
        for c in node.children:
            return "ensures coins older than " + c.value + " blk"
    return val


def collect_and_conditions(node: ScriptNode, xpubs: Optional[List[str]] = None) -> List[str]:
    """Collect all conditions under an AND node."""
    conditions: List[str] = []
    stack: List[ScriptNode] = [node]

    while len(stack) > 0:
        n = stack.pop()
        if n.normalized_value == "and":
            for child in n.children:
                stack.append(child)
        else:
            conditions.append(get_condition_text(n, xpubs))

    return conditions


def get_spending_paths(node: ScriptNode, xpubs: Optional[List[str]] = None) -> List[str]:
    """Build spending paths by traversing OR branches."""
    raw_paths: List[str] = []
    stack: List[ScriptNode] = [node]

    while len(stack) > 0:
        n = stack.pop()
        val = n.normalized_value

        # Skip empty (wsh, sh wrappers)
        if val == "":
            for child in n.children:
                stack.append(child)
            continue

        if val == "or":
            for child in reversed(n.children):
                stack.append(child)
        elif val == "and":
            conditions = collect_and_conditions(n, xpubs)
            conditions.reverse()
            if len(conditions) > 0:
                if len(conditions) == 1:
                    raw_paths.append(conditions[0])
                else:
                    path_text = "both " + conditions[0]
                    for i in range(1, len(conditions)):
                        if i == len(conditions) - 1:
                            path_text = path_text + ", and " + conditions[i]
                        else:
                            path_text = path_text + ", " + conditions[i]
                    raw_paths.append(path_text)
        else:
            raw_paths.append(get_condition_text(n, xpubs))

    paths: List[str] = []
    for i in range(len(raw_paths)):
        path_num = i + 1
        if path_num == 1:
            paths.append(str(path_num) + ". Spend if " + raw_paths[i])
        else:
            paths.append(str(path_num) + ". Alternatively, spend if " + raw_paths[i])

    return paths


def tree_repr(node: ScriptNode, normalize: bool = False) -> str:
    """Iterative tree representation."""
    lines: List[str] = []
    stack: List[tuple] = [(node, "", True, True)]

    while len(stack) > 0:
        n, prefix, is_last, is_root = stack.pop()

        # Get display value
        if normalize:
            node_val = n.normalized_value
        else:
            node_val = n.value

        # Skip empty values (wsh, sh when normalized)
        if node_val == "":
            for child in reversed(n.children):
                stack.append((child, prefix, is_last, is_root))
            continue

        # Collapse single-child operators: show as "parent(child)"
        if n.sem_type == SEMANTIC_OPERATOR and len(n.children) == 1:
            first_child = n.children[0]
            if normalize:
                child_val = first_child.normalized_value
            else:
                child_val = first_child.value
            display_value = node_val + "(" + child_val + ")"
            current_children = first_child.children
        else:
            display_value = node_val
            current_children = n.children

        # Build line
        if is_root:
            lines.append(display_value)
            child_prefix = ""
        else:
            if is_last:
                lines.append(prefix + "L__ " + display_value)
                child_prefix = prefix + "    "
            else:
                lines.append(prefix + "|-- " + display_value)
                child_prefix = prefix + "|   "

        # Add children in reverse order
        child_count = len(current_children)
        idx = child_count - 1
        for child in reversed(current_children):
            is_last_child = idx == child_count - 1
            stack.append((child, child_prefix, is_last_child, False))
            idx = idx - 1

    return "\n".join(lines) + "\n"
