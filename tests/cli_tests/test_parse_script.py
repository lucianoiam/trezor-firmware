#!/usr/bin/env micropython
import sys
sys.path.insert(0, "../../core/src/apps/bitcoin")

from parse_script import ScriptParser

script = "wsh(or_d(pk(@0/<0;1>/*),and_v(v:pkh(@1/<0;1>/*),older(1))))"

print("--- Script ---")
print(script)

# Parse once
root = ScriptParser(script).parse()

print("\n--- Script Tree (raw) ---")
print(root.tree_repr())

print("--- Policy Tree (normalized) ---")
print(root.tree_repr(normalize=True))

print("--- Spending Paths ---")
for step in root.get_spending_paths():
    print(step)
