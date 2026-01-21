"""
Miniscript to Bitcoin Script encoder.

Two-phase architecture:
1. emit_fragment() generates an intermediate assembly (list of Instruction objects)
2. assemble_bytecode() / assemble_text() converts assembly to final output

Limitations vs full spec (bitcoin.sipa.be/miniscript):
- Missing fragments: 0, 1, pk_h, ripemd160, hash256, and_n, multi_a
- No type checking (assumes valid miniscript input)
- No script size/ops limits validation
- Key derivation requires trezor.crypto.bip32 (no WIF keys)
"""

try:
    from typing import List, Optional
except ImportError:
    pass

try:
    from .parse_miniscript import MiniscriptNode
except (ImportError, KeyError):
    from parse_miniscript import MiniscriptNode

try:
    from ubinascii import hexlify, unhexlify
    def _hex(data: bytes) -> str:
        return hexlify(data).decode()
except ImportError:
    def _hex(data: bytes) -> str:
        return data.hex()
    unhexlify = bytes.fromhex

# Opcodes
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
OP_SHA256 = 0xA8
OP_HASH160 = 0xA9
OP_HASH256 = 0xAA
OP_CHECKSIG = 0xAC
OP_CHECKSIGVERIFY = 0xAD
OP_CHECKMULTISIG = 0xAE
OP_CHECKMULTISIGVERIFY = 0xAF
OP_CSV = 0xB2  # OP_CHECKSEQUENCEVERIFY
OP_CLTV = 0xB1  # OP_CHECKLOCKTIMEVERIFY
OP_BOOLAND = 0x9A
OP_BOOLOR = 0x9B

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
    OP_SHA256: "OP_SHA256",
    OP_HASH160: "OP_HASH160",
    OP_HASH256: "OP_HASH256",
    OP_CHECKSIG: "OP_CHECKSIG",
    OP_CHECKSIGVERIFY: "OP_CHECKSIGVERIFY",
    OP_CHECKMULTISIG: "OP_CHECKMULTISIG",
    OP_CHECKMULTISIGVERIFY: "OP_CHECKMULTISIGVERIFY",
    OP_CSV: "OP_CSV",
    OP_CLTV: "OP_CLTV",
    OP_BOOLAND: "OP_BOOLAND",
    OP_BOOLOR: "OP_BOOLOR",
}

# OP_PUSHNUM_1 through OP_PUSHNUM_16
for i in range(1, 17):
    OPCODE_NAMES[OP_1 + i - 1] = f"OP_PUSHNUM_{i}"


class Instruction:
    """
    Intermediate assembly instruction.

    Types:
    - OP: Single opcode (value is int opcode)
    - PUSH_NUM: Push a number (value is int)
    - PUSH_BYTES: Push raw bytes (value is bytes)
    """
    __slots__ = ("type", "int_value", "bytes_value")

    OP = 0
    PUSH_NUM = 1
    PUSH_BYTES = 2

    def __init__(self, type: int, int_value: int = 0, bytes_value: bytes = b""):
        self.type = type
        self.int_value = int_value
        self.bytes_value = bytes_value

    def __repr__(self) -> str:
        if self.type == self.OP:
            return f"OP({OPCODE_NAMES.get(self.int_value, hex(self.int_value))})"
        elif self.type == self.PUSH_NUM:
            return f"PUSH_NUM({self.int_value})"
        else:
            return f"PUSH_BYTES({_hex(self.bytes_value)})"


def op(opcode: int) -> Instruction:
    """Create an opcode instruction."""
    return Instruction(Instruction.OP, int_value=opcode)


def push_num(n: int) -> Instruction:
    """Create a push number instruction."""
    return Instruction(Instruction.PUSH_NUM, int_value=n)


def push_bytes(data: bytes) -> Instruction:
    """Create a push bytes instruction."""
    return Instruction(Instruction.PUSH_BYTES, bytes_value=data)


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


def emit_fragment(
    node: MiniscriptNode,
    xpubs: Optional[List[str]] = None,
    change: int = 0,
    index: int = 0,
) -> List[Instruction]:
    """
    Emit assembly instructions for a miniscript fragment.

    This is phase 1 of the two-phase encoding process.
    Returns a list of Instruction objects representing the script.
    """
    val = node.value
    instructions: List[Instruction] = []

    # Handle prefix wrappers first (applied after inner encoding)
    prefix = ""
    while len(val) >= 2 and val[1] == ":" and val[0] in "ascdvjnlut":
        prefix = val[0] + prefix  # Accumulate prefixes in reverse
        val = val[2:]

    # Encode the base fragment
    if val in ("pk", "pk_k"):
        # pk(key) -> <key> CHECKSIG
        key = derive_pubkey(node.children[0].value, xpubs, change, index)
        instructions.append(push_bytes(key))
        instructions.append(op(OP_CHECKSIG))

    elif val == "pkh":
        # pkh(key) -> DUP HASH160 <HASH160(key)> EQUALVERIFY CHECKSIG
        key = derive_pubkey(node.children[0].value, xpubs, change, index)
        key_hash = hash160(key)
        instructions.append(op(OP_DUP))
        instructions.append(op(OP_HASH160))
        instructions.append(push_bytes(key_hash))
        instructions.append(op(OP_EQUALVERIFY))
        instructions.append(op(OP_CHECKSIG))

    elif val == "older":
        # older(n) -> <n> CSV
        n = int(node.children[0].value)
        instructions.append(push_num(n))
        instructions.append(op(OP_CSV))

    elif val == "after":
        # after(n) -> <n> CLTV
        n = int(node.children[0].value)
        instructions.append(push_num(n))
        instructions.append(op(OP_CLTV))

    elif val == "sha256":
        # sha256(h) -> SIZE 32 EQUALVERIFY SHA256 <h> EQUAL
        h_bytes = unhexlify(node.children[0].value)
        instructions.append(op(OP_SIZE))
        instructions.append(push_num(32))
        instructions.append(op(OP_EQUALVERIFY))
        instructions.append(op(OP_SHA256))
        instructions.append(push_bytes(h_bytes))
        instructions.append(op(OP_EQUAL))

    elif val == "hash160":
        # hash160(h) -> SIZE 32 EQUALVERIFY HASH160 <h> EQUAL
        h_bytes = unhexlify(node.children[0].value)
        instructions.append(op(OP_SIZE))
        instructions.append(push_num(32))
        instructions.append(op(OP_EQUALVERIFY))
        instructions.append(op(OP_HASH160))
        instructions.append(push_bytes(h_bytes))
        instructions.append(op(OP_EQUAL))

    elif val == "and_v":
        # and_v(X,Y) -> [X] [Y]
        instructions.extend(emit_fragment(node.children[0], xpubs, change, index))
        instructions.extend(emit_fragment(node.children[1], xpubs, change, index))

    elif val == "and_b":
        # and_b(X,Y) -> [X] [Y] BOOLAND
        instructions.extend(emit_fragment(node.children[0], xpubs, change, index))
        instructions.extend(emit_fragment(node.children[1], xpubs, change, index))
        instructions.append(op(OP_BOOLAND))

    elif val == "or_b":
        # or_b(X,Z) -> [X] [Z] BOOLOR
        instructions.extend(emit_fragment(node.children[0], xpubs, change, index))
        instructions.extend(emit_fragment(node.children[1], xpubs, change, index))
        instructions.append(op(OP_BOOLOR))

    elif val == "or_c":
        # or_c(X,Z) -> [X] NOTIF [Z] ENDIF
        instructions.extend(emit_fragment(node.children[0], xpubs, change, index))
        instructions.append(op(OP_NOTIF))
        instructions.extend(emit_fragment(node.children[1], xpubs, change, index))
        instructions.append(op(OP_ENDIF))

    elif val == "or_d":
        # or_d(X,Z) -> [X] IFDUP NOTIF [Z] ENDIF
        instructions.extend(emit_fragment(node.children[0], xpubs, change, index))
        instructions.append(op(OP_IFDUP))
        instructions.append(op(OP_NOTIF))
        instructions.extend(emit_fragment(node.children[1], xpubs, change, index))
        instructions.append(op(OP_ENDIF))

    elif val == "or_i":
        # or_i(X,Z) -> IF [X] ELSE [Z] ENDIF
        instructions.append(op(OP_IF))
        instructions.extend(emit_fragment(node.children[0], xpubs, change, index))
        instructions.append(op(OP_ELSE))
        instructions.extend(emit_fragment(node.children[1], xpubs, change, index))
        instructions.append(op(OP_ENDIF))

    elif val == "andor":
        # andor(X,Y,Z) -> [X] NOTIF [Z] ELSE [Y] ENDIF
        instructions.extend(emit_fragment(node.children[0], xpubs, change, index))
        instructions.append(op(OP_NOTIF))
        instructions.extend(emit_fragment(node.children[2], xpubs, change, index))
        instructions.append(op(OP_ELSE))
        instructions.extend(emit_fragment(node.children[1], xpubs, change, index))
        instructions.append(op(OP_ENDIF))

    elif val == "thresh":
        # thresh(k,X1,...,Xn) -> [X1] [X2] ADD ... [Xn] ADD <k> EQUAL
        k = int(node.children[0].value)
        subs = node.children[1:]
        if len(subs) > 0:
            instructions.extend(emit_fragment(subs[0], xpubs, change, index))
            for sub in subs[1:]:
                instructions.extend(emit_fragment(sub, xpubs, change, index))
                instructions.append(op(OP_ADD))
        instructions.append(push_num(k))
        instructions.append(op(OP_EQUAL))

    elif val == "multi":
        # multi(k,key1,...,keyn) -> <k> <key1> ... <keyn> <n> CHECKMULTISIG
        k = int(node.children[0].value)
        keys = [derive_pubkey(c.value, xpubs, change, index) for c in node.children[1:]]
        n = len(keys)
        instructions.append(push_num(k))
        for key in keys:
            instructions.append(push_bytes(key))
        instructions.append(push_num(n))
        instructions.append(op(OP_CHECKMULTISIG))

    elif val in ("wsh", "sh"):
        # Descriptor wrappers - just encode the inner miniscript
        if node.children:
            instructions.extend(emit_fragment(node.children[0], xpubs, change, index))

    else:
        raise ValueError(f"Unknown miniscript fragment: {val}")

    # Apply prefix wrappers in reverse order (innermost first)
    for p in prefix:
        if p == "a":
            # a:X -> TOALTSTACK [X] FROMALTSTACK
            instructions = [op(OP_TOALTSTACK)] + instructions + [op(OP_FROMALTSTACK)]
        elif p == "s":
            # s:X -> SWAP [X]
            instructions = [op(OP_SWAP)] + instructions
        elif p == "c":
            # c:X -> [X] CHECKSIG
            instructions = instructions + [op(OP_CHECKSIG)]
        elif p == "d":
            # d:X -> DUP IF [X] ENDIF
            instructions = [op(OP_DUP), op(OP_IF)] + instructions + [op(OP_ENDIF)]
        elif p == "v":
            # v:X -> [X] VERIFY (or combine with last opcode)
            if instructions and instructions[-1].type == Instruction.OP:
                last_op = instructions[-1].int_value
                if last_op == OP_CHECKSIG:
                    instructions[-1] = op(OP_CHECKSIGVERIFY)
                elif last_op == OP_CHECKMULTISIG:
                    instructions[-1] = op(OP_CHECKMULTISIGVERIFY)
                elif last_op == OP_EQUAL:
                    instructions[-1] = op(OP_EQUALVERIFY)
                else:
                    instructions.append(op(OP_VERIFY))
            else:
                instructions.append(op(OP_VERIFY))
        elif p == "j":
            # j:X -> SIZE 0NOTEQUAL IF [X] ENDIF
            instructions = [op(OP_SIZE), op(OP_0NOTEQUAL), op(OP_IF)] + instructions + [op(OP_ENDIF)]
        elif p == "n":
            # n:X -> [X] 0NOTEQUAL
            instructions = instructions + [op(OP_0NOTEQUAL)]
        elif p == "l":
            # l:X -> IF 0 ELSE [X] ENDIF (same as or_i(0,X))
            instructions = [op(OP_IF), op(OP_0), op(OP_ELSE)] + instructions + [op(OP_ENDIF)]
        elif p == "u":
            # u:X -> IF [X] ELSE 0 ENDIF (same as or_i(X,0))
            instructions = [op(OP_IF)] + instructions + [op(OP_ELSE), op(OP_0), op(OP_ENDIF)]
        elif p == "t":
            # t:X -> [X] 1 (same as and_v(X,1))
            instructions = instructions + [op(OP_1)]

    return instructions


def assemble_bytecode(instructions: List[Instruction]) -> bytes:
    """
    Assemble instructions to bytecode.

    This is phase 2a of the two-phase encoding process.
    """
    result = b""

    for instr in instructions:
        if instr.type == Instruction.OP:
            result += bytes([instr.int_value])
        elif instr.type == Instruction.PUSH_NUM:
            n = instr.int_value
            if n == 0:
                result += bytes([OP_0])
            elif 1 <= n <= 16:
                result += bytes([OP_1 + n - 1])
            else:
                # Minimal encoding for larger numbers
                length = (n.bit_length() + 7) // 8
                data = bytearray(n.to_bytes(length, "little"))
                # If MSB is set, append 0x00 to keep positive
                if data[-1] & 0x80:
                    data.append(0x00)
                result += bytes([len(data)]) + bytes(data)
        elif instr.type == Instruction.PUSH_BYTES:
            data = instr.bytes_value
            length = len(data)
            if length < 0x4C:
                result += bytes([length]) + data
            elif length <= 0xFF:
                result += bytes([0x4C, length]) + data
            elif length <= 0xFFFF:
                result += bytes([0x4D, length & 0xFF, length >> 8]) + data
            else:
                raise ValueError("Data too large to push")

    return result


def assemble_asm(instructions: List[Instruction]) -> str:
    """
    Assemble instructions to human-readable assembly text.

    This is phase 2b of the two-phase encoding process.
    """
    parts: List[str] = []

    for instr in instructions:
        if instr.type == Instruction.OP:
            parts.append(OPCODE_NAMES.get(instr.int_value, f"0x{instr.int_value:02x}"))
        elif instr.type == Instruction.PUSH_NUM:
            n = instr.int_value
            if n == 0:
                parts.append("OP_0")
            elif 1 <= n <= 16:
                parts.append(f"OP_PUSHNUM_{n}")
            else:
                # Show raw hex for larger numbers
                length = (n.bit_length() + 7) // 8
                data = bytearray(n.to_bytes(length, "little"))
                if data[-1] & 0x80:
                    data.append(0x00)
                parts.append(_hex(bytes(data)))
        elif instr.type == Instruction.PUSH_BYTES:
            parts.append(_hex(instr.bytes_value))

    return " ".join(parts)


# Output format constants
FORMAT_BYTECODE = "bytecode"
FORMAT_ASM = "asm"


def encode_miniscript(
    node: MiniscriptNode,
    xpubs: Optional[List[str]] = None,
    change: int = 0,
    index: int = 0,
    format: str = FORMAT_BYTECODE,
):
    """
    Encode a miniscript tree to Bitcoin Script.

    Two-phase process:
    1. emit_fragment() generates intermediate assembly
    2. assemble_bytecode() or assemble_asm() produces final output

    Args:
        node: Parsed MiniscriptNode tree
        xpubs: Optional list of xpub strings for resolving @N references
        change: Value to use for <M;N> ranges in key paths (0 or 1)
        index: Value to use for * wildcard in key paths
        format: Output format - "bytecode" (default) or "asm"

    Returns:
        bytes if format="bytecode", str if format="asm"
    """
    # Phase 1: Generate assembly
    instructions = emit_fragment(node, xpubs, change, index)

    # Phase 2: Assemble to requested format
    if format == FORMAT_ASM:
        return assemble_asm(instructions)
    else:
        return assemble_bytecode(instructions)
