"""
Miniscript to Bitcoin Script encoder.

Limitations vs full spec (bitcoin.sipa.be/miniscript):
- Missing fragments: 0, 1, pk_h, ripemd160, hash256, and_n, multi_a
- No type checking (assumes valid miniscript input)
- No script size/ops limits validation
- Key derivation requires trezor.crypto.bip32 (no WIF keys)
"""

try:
    from typing import List, Optional, Tuple
except ImportError:
    pass

try:
    from .parse_miniscript import MiniscriptNode
except (ImportError, KeyError):
    from parse_miniscript import MiniscriptNode

try:
    from ubinascii import hexlify
    def _hex(data: bytes) -> str:
        return hexlify(data).decode()
except ImportError:
    def _hex(data: bytes) -> str:
        return data.hex()
OP_0 = 0x00
OP_1 = 0x51
OP_16 = 0x60
OP_DUP = 0x76
OP_IFDUP = 0x73
OP_IF = 0x63
OP_NOTIF = 0x64
OP_ELSE = 0x67
OP_ENDIF = 0x68
OP_VERIFY = 0x69
OP_RETURN = 0x6A
OP_TOALTSTACK = 0x6B
OP_FROMALTSTACK = 0x6C
OP_DROP = 0x75
OP_SIZE = 0x82
OP_EQUAL = 0x87
OP_EQUALVERIFY = 0x88
OP_0NOTEQUAL = 0x92
OP_ADD = 0x93
OP_SWAP = 0x7C
OP_HASH160 = 0xA9
OP_HASH256 = 0xAA
OP_CHECKSIG = 0xAC
OP_CHECKSIGVERIFY = 0xAD
OP_CHECKMULTISIG = 0xAE
OP_CHECKMULTISIGVERIFY = 0xAF
OP_CSV = 0xB2  # OP_CHECKSEQUENCEVERIFY
OP_CLTV = 0xB1  # OP_CHECKLOCKTIMEVERIFY

# Opcode names for text output
OPCODE_NAMES = {
    OP_0: "OP_0",
    OP_DUP: "OP_DUP",
    OP_IFDUP: "OP_IFDUP",
    OP_IF: "OP_IF",
    OP_NOTIF: "OP_NOTIF",
    OP_ELSE: "OP_ELSE",
    OP_ENDIF: "OP_ENDIF",
    OP_VERIFY: "OP_VERIFY",
    OP_RETURN: "OP_RETURN",
    OP_TOALTSTACK: "OP_TOALTSTACK",
    OP_FROMALTSTACK: "OP_FROMALTSTACK",
    OP_DROP: "OP_DROP",
    OP_SIZE: "OP_SIZE",
    OP_EQUAL: "OP_EQUAL",
    OP_EQUALVERIFY: "OP_EQUALVERIFY",
    OP_0NOTEQUAL: "OP_0NOTEQUAL",
    OP_ADD: "OP_ADD",
    OP_SWAP: "OP_SWAP",
    OP_HASH160: "OP_HASH160",
    OP_HASH256: "OP_HASH256",
    OP_CHECKSIG: "OP_CHECKSIG",
    OP_CHECKSIGVERIFY: "OP_CHECKSIGVERIFY",
    OP_CHECKMULTISIG: "OP_CHECKMULTISIG",
    OP_CHECKMULTISIGVERIFY: "OP_CHECKMULTISIGVERIFY",
    OP_CSV: "OP_CSV",
    OP_CLTV: "OP_CLTV",
}


def push_number(n: int) -> Tuple[bytes, str]:
    """Encode a number for Bitcoin Script, returns (bytecode, text)."""
    if n == 0:
        return bytes([OP_0]), "OP_0"
    if 1 <= n <= 16:
        return bytes([OP_1 + n - 1]), f"OP_PUSHNUM_{n}"
    # For larger numbers, use minimal encoding
    length = (n.bit_length() + 7) // 8
    data = bytearray(n.to_bytes(length, "little"))
    # If MSB is set, append 0x00 to keep positive
    if data[-1] & 0x80:
        data.append(0x00)
    return bytes([len(data)]) + bytes(data), _hex(bytes(data))


def push_bytes(data: bytes) -> Tuple[bytes, str]:
    """Push arbitrary bytes onto the stack, returns (bytecode, text)."""
    length = len(data)
    hex_str = _hex(data)
    if length < 0x4C:
        return bytes([length]) + data, hex_str
    elif length <= 0xFF:
        return bytes([0x4C, length]) + data, hex_str
    elif length <= 0xFFFF:
        return bytes([0x4D, length & 0xFF, length >> 8]) + data, hex_str
    else:
        raise ValueError("Data too large to push")


def derive_pubkey(
    key_expr: str,
    xpubs: Optional[List[str]] = None,
    change: int = 0,
    index: int = 0,
) -> bytes:
    """
    Derive a public key from a key expression.

    Supports:
    - Raw hex pubkey: "03adc58..."
    - xpub with path: "tpubDCZB6.../0/0"
    - Reference with path: "@0/<0;1>/*" (requires xpubs list)

    Args:
        change: Value to use for <M;N> ranges (0 or 1)
        index: Value to use for * wildcard
    """
    # Check if it's a reference like @0/<0;1>/*
    if key_expr.startswith("@"):
        if xpubs is None:
            raise ValueError("xpubs required to resolve reference")
        # Parse @N where N is the index
        rest = key_expr[1:]
        slash_idx = rest.find("/")
        if slash_idx == -1:
            idx = int(rest)
            path = ""
        else:
            idx = int(rest[:slash_idx])
            path = rest[slash_idx + 1:]  # path without leading slash
        if idx >= len(xpubs):
            raise ValueError("Reference out of range")
        base_key = xpubs[idx]
    elif "/" in key_expr:
        # xpub/path format
        slash_idx = key_expr.find("/")
        base_key = key_expr[:slash_idx]
        path = key_expr[slash_idx + 1:]
    else:
        # Raw hex pubkey or bare xpub
        if key_expr.startswith("xpub") or key_expr.startswith("tpub"):
            base_key = key_expr
            path = ""
        else:
            # Raw hex pubkey
            try:
                from ubinascii import unhexlify
            except ImportError:
                unhexlify = bytes.fromhex
            return unhexlify(key_expr)

    # Derive from xpub
    try:
        from trezor.crypto import bip32

        # Determine version based on prefix
        if base_key.startswith("tpub"):
            version = 0x043587CF  # testnet
        else:
            version = 0x0488B21E  # mainnet

        node = bip32.deserialize_public(base_key, version, "secp256k1")

        # Derive along path
        for part in path.split("/"):
            if not part:
                continue
            if part == "*":
                node.derive(index, True)
            elif part.startswith("<") and part.endswith(">"):
                # Range like <0;1> - use change parameter to select
                # NOTE: Assumes <0;1> pattern. Does not parse actual range values.
                # For <M;N> with M!=0 or N!=1, this would be incorrect.
                node.derive(change, True)
            else:
                node.derive(int(part), True)

        return node.public_key()

    except ImportError:
        raise ImportError("bip32 required for xpub derivation")


def hash160(data: bytes) -> bytes:
    """Compute HASH160 (RIPEMD160(SHA256(data)))."""
    try:
        from trezor.crypto.hashlib import ripemd160, sha256
        return ripemd160(sha256(data).digest()).digest()
    except ImportError:
        import hashlib
        sha = hashlib.sha256(data).digest()
        return hashlib.new("ripemd160", sha).digest()


def encode_fragment(
    node: MiniscriptNode,
    xpubs: Optional[List[str]] = None,
    change: int = 0,
    index: int = 0,
) -> Tuple[bytes, List[str]]:
    """
    Encode a miniscript fragment to Bitcoin Script.

    Returns (bytecode, text_parts) where text_parts is a list of opcode/data strings.
    """
    val = node.value
    bytecode = b""
    text_parts: List[str] = []

    # Handle prefix wrappers first (applied after inner encoding)
    prefix = ""
    while len(val) >= 2 and val[1] == ":" and val[0] in "ascdvjnlut":
        prefix = val[0] + prefix  # Accumulate prefixes in reverse
        val = val[2:]

    # Encode the base fragment
    if val in ("pk", "pk_k"):
        # pk(key) -> <key> CHECKSIG
        key = derive_pubkey(node.children[0].value, xpubs, change, index)
        bc, txt = push_bytes(key)
        bytecode += bc
        text_parts.append(txt)
        bytecode += bytes([OP_CHECKSIG])
        text_parts.append("OP_CHECKSIG")

    elif val == "pkh":
        # pkh(key) -> DUP HASH160 <HASH160(key)> EQUALVERIFY CHECKSIG
        key = derive_pubkey(node.children[0].value, xpubs, change, index)
        key_hash = hash160(key)
        bytecode += bytes([OP_DUP, OP_HASH160])
        text_parts.extend(["OP_DUP", "OP_HASH160"])
        bc, txt = push_bytes(key_hash)
        bytecode += bc
        text_parts.append(txt)
        bytecode += bytes([OP_EQUALVERIFY, OP_CHECKSIG])
        text_parts.extend(["OP_EQUALVERIFY", "OP_CHECKSIG"])

    elif val == "older":
        # older(n) -> <n> CSV
        n = int(node.children[0].value)
        bc, txt = push_number(n)
        bytecode += bc
        text_parts.append(txt)
        bytecode += bytes([OP_CSV])
        text_parts.append("OP_CSV")

    elif val == "after":
        # after(n) -> <n> CLTV
        n = int(node.children[0].value)
        bc, txt = push_number(n)
        bytecode += bc
        text_parts.append(txt)
        bytecode += bytes([OP_CLTV])
        text_parts.append("OP_CLTV")

    elif val == "sha256":
        # sha256(h) -> SIZE 32 EQUALVERIFY SHA256 <h> EQUAL
        h = node.children[0].value
        try:
            from ubinascii import unhexlify
        except ImportError:
            unhexlify = bytes.fromhex
        h_bytes = unhexlify(h)
        bytecode += bytes([OP_SIZE])
        text_parts.append("OP_SIZE")
        bc, txt = push_number(32)
        bytecode += bc
        text_parts.append(txt)
        bytecode += bytes([OP_EQUALVERIFY, 0xA8])  # 0xA8 = OP_SHA256
        text_parts.extend(["OP_EQUALVERIFY", "OP_SHA256"])
        bc, txt = push_bytes(h_bytes)
        bytecode += bc
        text_parts.append(txt)
        bytecode += bytes([OP_EQUAL])
        text_parts.append("OP_EQUAL")

    elif val == "hash160":
        # hash160(h) -> SIZE 32 EQUALVERIFY HASH160 <h> EQUAL
        h = node.children[0].value
        try:
            from ubinascii import unhexlify
        except ImportError:
            unhexlify = bytes.fromhex
        h_bytes = unhexlify(h)
        bytecode += bytes([OP_SIZE])
        text_parts.append("OP_SIZE")
        bc, txt = push_number(32)
        bytecode += bc
        text_parts.append(txt)
        bytecode += bytes([OP_EQUALVERIFY, OP_HASH160])
        text_parts.extend(["OP_EQUALVERIFY", "OP_HASH160"])
        bc, txt = push_bytes(h_bytes)
        bytecode += bc
        text_parts.append(txt)
        bytecode += bytes([OP_EQUAL])
        text_parts.append("OP_EQUAL")

    elif val == "and_v":
        # and_v(X,Y) -> [X] [Y]
        x_bc, x_txt = encode_fragment(node.children[0], xpubs, change, index)
        y_bc, y_txt = encode_fragment(node.children[1], xpubs, change, index)
        bytecode += x_bc + y_bc
        text_parts.extend(x_txt)
        text_parts.extend(y_txt)

    elif val == "and_b":
        # and_b(X,Y) -> [X] [Y] BOOLAND
        x_bc, x_txt = encode_fragment(node.children[0], xpubs, change, index)
        y_bc, y_txt = encode_fragment(node.children[1], xpubs, change, index)
        bytecode += x_bc + y_bc + bytes([0x9A])  # 0x9A = OP_BOOLAND
        text_parts.extend(x_txt)
        text_parts.extend(y_txt)
        text_parts.append("OP_BOOLAND")

    elif val == "or_b":
        # or_b(X,Z) -> [X] [Z] BOOLOR
        x_bc, x_txt = encode_fragment(node.children[0], xpubs, change, index)
        z_bc, z_txt = encode_fragment(node.children[1], xpubs, change, index)
        bytecode += x_bc + z_bc + bytes([0x9B])  # 0x9B = OP_BOOLOR
        text_parts.extend(x_txt)
        text_parts.extend(z_txt)
        text_parts.append("OP_BOOLOR")

    elif val == "or_c":
        # or_c(X,Z) -> [X] NOTIF [Z] ENDIF
        x_bc, x_txt = encode_fragment(node.children[0], xpubs, change, index)
        z_bc, z_txt = encode_fragment(node.children[1], xpubs, change, index)
        bytecode += x_bc + bytes([OP_NOTIF]) + z_bc + bytes([OP_ENDIF])
        text_parts.extend(x_txt)
        text_parts.append("OP_NOTIF")
        text_parts.extend(z_txt)
        text_parts.append("OP_ENDIF")

    elif val == "or_d":
        # or_d(X,Z) -> [X] IFDUP NOTIF [Z] ENDIF
        x_bc, x_txt = encode_fragment(node.children[0], xpubs, change, index)
        z_bc, z_txt = encode_fragment(node.children[1], xpubs, change, index)
        bytecode += x_bc + bytes([OP_IFDUP, OP_NOTIF]) + z_bc + bytes([OP_ENDIF])
        text_parts.extend(x_txt)
        text_parts.extend(["OP_IFDUP", "OP_NOTIF"])
        text_parts.extend(z_txt)
        text_parts.append("OP_ENDIF")

    elif val == "or_i":
        # or_i(X,Z) -> IF [X] ELSE [Z] ENDIF
        x_bc, x_txt = encode_fragment(node.children[0], xpubs, change, index)
        z_bc, z_txt = encode_fragment(node.children[1], xpubs, change, index)
        bytecode += bytes([OP_IF]) + x_bc + bytes([OP_ELSE]) + z_bc + bytes([OP_ENDIF])
        text_parts.append("OP_IF")
        text_parts.extend(x_txt)
        text_parts.append("OP_ELSE")
        text_parts.extend(z_txt)
        text_parts.append("OP_ENDIF")

    elif val == "andor":
        # andor(X,Y,Z) -> [X] NOTIF [Z] ELSE [Y] ENDIF
        x_bc, x_txt = encode_fragment(node.children[0], xpubs, change, index)
        y_bc, y_txt = encode_fragment(node.children[1], xpubs, change, index)
        z_bc, z_txt = encode_fragment(node.children[2], xpubs, change, index)
        bytecode += x_bc + bytes([OP_NOTIF]) + z_bc + bytes([OP_ELSE]) + y_bc + bytes([OP_ENDIF])
        text_parts.extend(x_txt)
        text_parts.append("OP_NOTIF")
        text_parts.extend(z_txt)
        text_parts.append("OP_ELSE")
        text_parts.extend(y_txt)
        text_parts.append("OP_ENDIF")

    elif val == "thresh":
        # thresh(k,X1,...,Xn) -> [X1] [X2] ADD ... [Xn] ADD <k> EQUAL
        k = int(node.children[0].value)
        subs = node.children[1:]
        if len(subs) > 0:
            first_bc, first_txt = encode_fragment(subs[0], xpubs, change, index)
            bytecode += first_bc
            text_parts.extend(first_txt)
            for sub in subs[1:]:
                sub_bc, sub_txt = encode_fragment(sub, xpubs, change, index)
                bytecode += sub_bc + bytes([OP_ADD])
                text_parts.extend(sub_txt)
                text_parts.append("OP_ADD")
        bc, txt = push_number(k)
        bytecode += bc
        text_parts.append(txt)
        bytecode += bytes([OP_EQUAL])
        text_parts.append("OP_EQUAL")

    elif val == "multi":
        # multi(k,key1,...,keyn) -> <k> <key1> ... <keyn> <n> CHECKMULTISIG
        k = int(node.children[0].value)
        keys = [derive_pubkey(c.value, xpubs, change, index) for c in node.children[1:]]
        n = len(keys)
        bc, txt = push_number(k)
        bytecode += bc
        text_parts.append(txt)
        for key in keys:
            bc, txt = push_bytes(key)
            bytecode += bc
            text_parts.append(txt)
        bc, txt = push_number(n)
        bytecode += bc
        text_parts.append(txt)
        bytecode += bytes([OP_CHECKMULTISIG])
        text_parts.append("OP_CHECKMULTISIG")

    elif val in ("wsh", "sh"):
        # Descriptor wrappers - just encode the inner miniscript
        if node.children:
            inner_bc, inner_txt = encode_fragment(node.children[0], xpubs, change, index)
            bytecode += inner_bc
            text_parts.extend(inner_txt)

    else:
        raise ValueError(f"Unknown miniscript fragment: {val}")

    # Apply prefix wrappers in reverse order (innermost first)
    for p in prefix:
        if p == "a":
            # a:X -> TOALTSTACK [X] FROMALTSTACK
            bytecode = bytes([OP_TOALTSTACK]) + bytecode + bytes([OP_FROMALTSTACK])
            text_parts = ["OP_TOALTSTACK"] + text_parts + ["OP_FROMALTSTACK"]
        elif p == "s":
            # s:X -> SWAP [X]
            bytecode = bytes([OP_SWAP]) + bytecode
            text_parts = ["OP_SWAP"] + text_parts
        elif p == "c":
            # c:X -> [X] CHECKSIG
            bytecode = bytecode + bytes([OP_CHECKSIG])
            text_parts = text_parts + ["OP_CHECKSIG"]
        elif p == "d":
            # d:X -> DUP IF [X] ENDIF
            bytecode = bytes([OP_DUP, OP_IF]) + bytecode + bytes([OP_ENDIF])
            text_parts = ["OP_DUP", "OP_IF"] + text_parts + ["OP_ENDIF"]
        elif p == "v":
            # v:X -> [X] VERIFY (or combine with last opcode)
            # Special case: CHECKSIG -> CHECKSIGVERIFY, etc.
            if bytecode and bytecode[-1] == OP_CHECKSIG:
                bytecode = bytecode[:-1] + bytes([OP_CHECKSIGVERIFY])
                text_parts = text_parts[:-1] + ["OP_CHECKSIGVERIFY"]
            elif bytecode and bytecode[-1] == OP_CHECKMULTISIG:
                bytecode = bytecode[:-1] + bytes([OP_CHECKMULTISIGVERIFY])
                text_parts = text_parts[:-1] + ["OP_CHECKMULTISIGVERIFY"]
            elif bytecode and bytecode[-1] == OP_EQUAL:
                bytecode = bytecode[:-1] + bytes([OP_EQUALVERIFY])
                text_parts = text_parts[:-1] + ["OP_EQUALVERIFY"]
            else:
                bytecode = bytecode + bytes([OP_VERIFY])
                text_parts = text_parts + ["OP_VERIFY"]
        elif p == "j":
            # j:X -> SIZE 0NOTEQUAL IF [X] ENDIF
            bytecode = bytes([OP_SIZE, OP_0NOTEQUAL, OP_IF]) + bytecode + bytes([OP_ENDIF])
            text_parts = ["OP_SIZE", "OP_0NOTEQUAL", "OP_IF"] + text_parts + ["OP_ENDIF"]
        elif p == "n":
            # n:X -> [X] 0NOTEQUAL
            bytecode = bytecode + bytes([OP_0NOTEQUAL])
            text_parts = text_parts + ["OP_0NOTEQUAL"]
        elif p == "l":
            # l:X -> IF 0 ELSE [X] ENDIF (same as or_i(0,X))
            bytecode = bytes([OP_IF, OP_0, OP_ELSE]) + bytecode + bytes([OP_ENDIF])
            text_parts = ["OP_IF", "OP_0", "OP_ELSE"] + text_parts + ["OP_ENDIF"]
        elif p == "u":
            # u:X -> IF [X] ELSE 0 ENDIF (same as or_i(X,0))
            bytecode = bytes([OP_IF]) + bytecode + bytes([OP_ELSE, OP_0, OP_ENDIF])
            text_parts = ["OP_IF"] + text_parts + ["OP_ELSE", "OP_0", "OP_ENDIF"]
        elif p == "t":
            # t:X -> [X] 1 (same as and_v(X,1))
            bytecode = bytecode + bytes([OP_1])
            text_parts = text_parts + ["OP_PUSHNUM_1"]

    return bytecode, text_parts


def encode_miniscript(
    node: MiniscriptNode,
    xpubs: Optional[List[str]] = None,
    change: int = 0,
    index: int = 0,
) -> Tuple[bytes, str]:
    """
    Encode a miniscript tree to Bitcoin Script.

    Args:
        node: Parsed MiniscriptNode tree
        xpubs: Optional list of xpub strings for resolving @N references
        change: Value to use for <M;N> ranges in key paths (0 or 1)
        index: Value to use for * wildcard in key paths

    Returns:
        Tuple of (bytecode, text_representation)
    """
    bytecode, text_parts = encode_fragment(node, xpubs, change, index)
    text = " ".join(text_parts)
    return bytecode, text
