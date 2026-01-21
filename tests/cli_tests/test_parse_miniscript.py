#!/usr/bin/env micropython
import sys
sys.path.insert(0, "../../core/src/apps/bitcoin")

from parse_miniscript import parse_miniscript
from policy_rules import format_tree, get_spending_rules

miniscript = "wsh(or_d(pk(@0/<0;1>/*),and_v(v:pkh(@1/<0;1>/*),older(1))))"

print("--- Miniscript ---")
print(miniscript)

# Parse once
root = parse_miniscript(miniscript)

print("\n--- Miniscript Tree (raw) ---")
print(format_tree(root))

print("--- Policy Tree (normalized) ---")
print(format_tree(root, normalize=True))

print("--- Spending Rules ---")
for rule in get_spending_rules(root):
    print(rule)
