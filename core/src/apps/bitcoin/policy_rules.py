try:
    from typing import List, Optional
except ImportError:
    pass

try:
    from .parse_miniscript import MiniscriptNode, SEMANTIC_OPERATOR
except (ImportError, KeyError):
    from parse_miniscript import MiniscriptNode, SEMANTIC_OPERATOR


def format_condition(node: MiniscriptNode, xpubs: Optional[List[str]] = None) -> str:
    """Get human-readable condition for a leaf node."""
    val = node.normalized_value
    if val == "pk":
        for c in node.children:
            return "signs with " + c.value
    elif val == "older":
        for c in node.children:
            return "coins older than " + c.value + " blk"
    return val


def collect_conditions(node: MiniscriptNode, xpubs: Optional[List[str]] = None) -> List[str]:
    """Collect all conditions under an AND node."""
    conditions: List[str] = []
    stack: List[MiniscriptNode] = [node]

    while len(stack) > 0:
        n = stack.pop()
        if n.normalized_value == "and":
            for child in n.children:
                stack.append(child)
        else:
            conditions.append(format_condition(n, xpubs))

    return conditions


def get_spending_rules(node: MiniscriptNode, xpubs: Optional[List[str]] = None) -> List[str]:
    """Build spending rules by traversing OR branches."""
    raw_paths: List[str] = []
    stack: List[MiniscriptNode] = [node]

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
            conditions = collect_conditions(n, xpubs)
            conditions.reverse()
            if len(conditions) > 0:
                if len(conditions) == 1:
                    raw_paths.append(conditions[0])
                else:
                    path_text = conditions[0]
                    for i in range(1, len(conditions)):
                        if i == len(conditions) - 1:
                            path_text = path_text + " and " + conditions[i]
                        else:
                            path_text = path_text + ", " + conditions[i]
                    raw_paths.append(path_text)
        else:
            raw_paths.append(format_condition(n, xpubs))

    paths: List[str] = []
    for i in range(len(raw_paths)):
        if i == 0:
            paths.append("Spend if " + raw_paths[i])
        else:
            paths.append("Also spend if " + raw_paths[i])

    return paths


def format_tree(node: MiniscriptNode, normalize: bool = False) -> str:
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
