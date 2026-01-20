from typing import List, Optional


SEMANTIC_OPERATOR = 0
SEMANTIC_OPERAND = 1

ALNUM = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def isalnum(c: str) -> bool:
    return c in ALNUM


class PolicyNode:
    def __init__(
        self,
        value: str,
        sem_type: int,
        children: Optional[List["PolicyNode"]] = None,
    ) -> None:
        self.value = value
        self.sem_type = sem_type
        self.children: List["PolicyNode"] = children if children else []

    def _get_condition_text(self, xpubs: Optional[List[str]] = None) -> str:
        # Get human-readable condition for a leaf node
        if self.value == "pk":
            for c in self.children:
                key_ref = c.value
                # Replace @N with actual xpub if available
                #if xpubs is not None and key_ref.startswith("@"):
                #    idx_end = 1
                #    while idx_end < len(key_ref) and key_ref[idx_end].isdigit():
                #        idx_end = idx_end + 1
                #    idx_str = key_ref[1:idx_end]
                #    if len(idx_str) > 0:
                #        idx = int(idx_str)
                #        if idx < len(xpubs):
                #            key_ref = xpubs[idx] + key_ref[idx_end:]
                return "provides signature " + key_ref
        elif self.value == "older":
            for c in self.children:
                return "ensures coins older than " + c.value + " blk"
        return self.value

    def _collect_and_conditions(self, xpubs: Optional[List[str]] = None) -> List[str]:
        # Collect all conditions under an AND node
        conditions: List[str] = []
        stack: List["PolicyNode"] = [self]

        while len(stack) > 0:
            node = stack.pop()
            if node.value == "and":
                for child in node.children:
                    stack.append(child)
            else:
                conditions.append(node._get_condition_text(xpubs))

        return conditions

    def get_spending_paths(self, xpubs: Optional[List[str]] = None) -> List[str]:
        # Build spending paths by traversing OR branches
        # Each OR creates alternative paths, AND combines conditions
        # First collect all paths, then number them
        raw_paths: List[str] = []

        # Stack holds nodes that represent spending alternatives
        stack: List["PolicyNode"] = [self]

        while len(stack) > 0:
            node = stack.pop()

            if node.value == "or":
                # OR creates alternatives - add children in reverse for correct order
                for child in reversed(node.children):
                    stack.append(child)
            elif node.value == "and":
                # AND combines conditions into one path
                conditions = node._collect_and_conditions(xpubs)
                # Reverse to get correct order
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
                # Single condition path
                raw_paths.append(node._get_condition_text(xpubs))

        # Now format with numbers
        paths: List[str] = []
        for i in range(len(raw_paths)):
            path_num = i + 1
            if path_num == 1:
                paths.append(str(path_num) + ". Spend if " + raw_paths[i])
            else:
                paths.append(str(path_num) + ". Alternatively, spend if " + raw_paths[i])

        return paths

    def rules_repr(self, xpubs: Optional[List[str]] = None) -> List[str]:
        paths = self.get_spending_paths(xpubs)
        return paths

    def tree_repr(self) -> str:
        # Iterative tree representation
        lines: List[str] = []
        # Stack holds: (node, prefix, is_last, is_root)
        stack: List[tuple] = [(self, "", True, True)]

        while len(stack) > 0:
            node, prefix, is_last, is_root = stack.pop()

            # Determine display value
            if node.sem_type == SEMANTIC_OPERATOR and len(node.children) == 1:
                first_child_value = ""
                for c in node.children:
                    first_child_value = c.value
                    break
                display_value = node.value + "(" + first_child_value + ")"
                current_children: List["PolicyNode"] = []
            else:
                display_value = node.value
                current_children = node.children

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

            # Add children in reverse order so they pop in correct order
            child_count = len(current_children)
            idx = child_count - 1
            for child in reversed(current_children):
                is_last_child = idx == child_count - 1
                stack.append((child, child_prefix, is_last_child, False))
                idx = idx - 1

        return "\n".join(lines) + "\n"


def miniscript_to_policy(miniscript: str) -> str:
    result = miniscript

    if result.startswith("wsh(") and result.endswith(")"):
        result = result[4:-1]
    elif result.startswith("sh(") and result.endswith(")"):
        result = result[3:-1]

    result = result.replace("or_b(", "or(")
    result = result.replace("or_c(", "or(")
    result = result.replace("or_d(", "or(")
    result = result.replace("or_i(", "or(")
    result = result.replace("or_n(", "or(")
    result = result.replace("or_v(", "or(")
    result = result.replace("and_b(", "and(")
    result = result.replace("and_c(", "and(")
    result = result.replace("and_d(", "and(")
    result = result.replace("and_i(", "and(")
    result = result.replace("and_n(", "and(")
    result = result.replace("and_v(", "and(")

    result = result.replace("a:", "")
    result = result.replace("s:", "")
    result = result.replace("c:", "")
    result = result.replace("d:", "")
    result = result.replace("v:", "")
    result = result.replace("j:", "")
    result = result.replace("n:", "")
    result = result.replace("l:", "")
    result = result.replace("u:", "")
    result = result.replace("t:", "")

    result = result.replace("pk_k(", "pk(")
    result = result.replace("pk_h(", "pk(")
    result = result.replace("pkh(", "pk(")

    return result


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


class PolicyParser:
    def __init__(self, text: str) -> None:
        self.tokens = tokenize(text)
        self.pos = 0

    def parse(self) -> PolicyNode:
        # Iterative parsing using explicit stack
        # Stack holds parent nodes waiting for children
        stack: List[PolicyNode] = []
        root: Optional[PolicyNode] = None

        while self.pos < len(self.tokens):
            token = self.tokens[self.pos]
            self.pos += 1

            if token == ",":
                continue
            elif token == ")":
                # Pop completed node from stack
                if len(stack) > 1:
                    stack.pop()
                elif len(stack) == 1:
                    root = stack.pop()
                continue

            # Check if this token starts a function call
            if self.pos < len(self.tokens) and self.tokens[self.pos] == "(":
                node = PolicyNode(token, SEMANTIC_OPERATOR)
                self.pos += 1  # consume "("
            else:
                node = PolicyNode(token, SEMANTIC_OPERAND)

            # Attach to parent if exists
            if len(stack) > 0:
                parent = stack[len(stack) - 1]
                parent.children.append(node)

            # If operator, push to stack to collect children
            if node.sem_type == SEMANTIC_OPERATOR:
                stack.append(node)
            elif root is None and len(stack) == 0:
                root = node

        # Handle case where root is still on stack
        if root is None and len(stack) > 0:
            root = stack[0]

        if root is None:
            raise ValueError("Failed to parse policy")

        return root


if __name__ == "__main__":
    script = "wsh(or_d(pk(@0/<0;1>/*),and_v(v:pkh(@1/<0;1>/*),older(1))))"
    policy = miniscript_to_policy(script)

    print("--- Script ---")
    print(script)

    print("\n--- Policy ---")
    print(policy)

    root = PolicyParser(policy).parse()

    print("\n--- Steps ---")
    for step in root.rules_repr(xpubs=['0','1']):
        print(step)

    print("\n--- Tree ---")
    print(root.tree_repr())
