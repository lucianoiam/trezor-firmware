#!/usr/bin/env python3
"""Test miniscript parsing and encoding."""
import sys
sys.path.insert(0, "../../core/src/apps/bitcoin")

from parse_miniscript import parse_miniscript
from policy_rules import abbreviate_xpubs, format_tree, get_spending_rules
from encode_miniscript import encode_miniscript, derive_pubkey
from bip32_utils import derive_pubkey_from_xpub

# Monkey-patch derive_pubkey to use our standalone bip32_utils
_original_derive = derive_pubkey.__code__
def _patched_derive(key_expr, xpubs=None):
    if key_expr.startswith("@"):
        rest = key_expr[1:]
        slash_idx = rest.find("/")
        if slash_idx == -1:
            idx = int(rest)
            path = ""
        else:
            idx = int(rest[:slash_idx])
            path = rest[slash_idx + 1:]
        base_key = xpubs[idx]
    elif "/" in key_expr:
        slash_idx = key_expr.find("/")
        base_key = key_expr[:slash_idx]
        path = key_expr[slash_idx + 1:]
    elif key_expr.startswith(("xpub", "tpub")):
        base_key = key_expr
        path = ""
    else:
        return bytes.fromhex(key_expr)
    return derive_pubkey_from_xpub(base_key, path)

# Patch the module
import encode_miniscript as em
em.derive_pubkey = _patched_derive

# Test data
xpubs = [
    "tpubDCZB6sR48s4T5Cr8qHUYSZEFCQMMHRg8AoVKVmvcAP5bRw7ArDKeoNwKAJujV3xCPkBvXH5ejSgbgyN6kREmF7sMd41NdbuHa8n1DZNxSMg",
    "tpubDCNhwLKYSSu2FKssoMziAdwhAAKS3bASH7wZYkNmJ7sU5hW9LgDaAQPqe7ivAkskSF29B1CkRRg4g2mbovXgAL9Mby6i9xBdhZh2txDeSLb",
]

print("=" * 60)
print("Test 1: Parse and display miniscript with references")
print("=" * 60)

miniscript = "wsh(or_d(pk(@0/<0;1>/*),and_v(v:pkh(@1/<0;1>/*),older(1))))"
print("Input:", miniscript)

root = parse_miniscript(miniscript)

print("\nMiniscript tree (raw):")
print(format_tree(root))

print("Policy tree (normalized):")
print(format_tree(root, normalize=True))

print("Spending rules (with abbreviated xpubs):")
for rule in get_spending_rules(root, abbreviate_xpubs(xpubs)):
    print(rule)

print("\nEncoded (with xpub derivation):")
bytecode, text = encode_miniscript(root, xpubs)
print("Text:", text)
print("Hex:", bytecode.hex())

print("\n" + "=" * 60)
print("Test 2: Exact match with adys.dev/miniscript example")
print("=" * 60)

miniscript_exact = "or_d(pk(tpubDCZB6sR48s4T5Cr8qHUYSZEFCQMMHRg8AoVKVmvcAP5bRw7ArDKeoNwKAJujV3xCPkBvXH5ejSgbgyN6kREmF7sMd41NdbuHa8n1DZNxSMg/0/0),and_v(v:pkh(tpubDCNhwLKYSSu2FKssoMziAdwhAAKS3bASH7wZYkNmJ7sU5hW9LgDaAQPqe7ivAkskSF29B1CkRRg4g2mbovXgAL9Mby6i9xBdhZh2txDeSLb/0/0),older(1)))"

expected = "03adc58245cf28406af0ef5cc24b8afba7f1be6c72f279b642d85c48798685f862 OP_CHECKSIG OP_IFDUP OP_NOTIF OP_DUP OP_HASH160 01551d33fcb0bffe32d71e08449107d6945b56e8 OP_EQUALVERIFY OP_CHECKSIGVERIFY OP_PUSHNUM_1 OP_CSV OP_ENDIF"

print("Input:", miniscript_exact[:60] + "...")

root = parse_miniscript(miniscript_exact)
bytecode, text = encode_miniscript(root)

print("Output:", text)
print("Expected:", expected)
print()

if text == expected:
    print("✓ PASS: Output matches expected")
else:
    print("✗ FAIL: Output differs")
    sys.exit(1)
