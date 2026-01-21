#!/usr/bin/env micropython
import sys
sys.path.insert(0, "../../core/src/apps/bitcoin")

from parse_miniscript import parse_miniscript, tree_repr, get_spending_paths

miniscript = "wsh(or_d(pk(@0/<0;1>/*),and_v(v:pkh(@1/<0;1>/*),older(1))))"

print("--- Miniscript ---")
print(miniscript)

# Parse once
root = parse_miniscript(miniscript)

print("\n--- Miniscript Tree (raw) ---")
print(tree_repr(root))

print("--- Policy Tree (normalized) ---")
print(tree_repr(root, normalize=True))

print("--- Spending Paths ---")
for step in get_spending_paths(root):
    print(step)
