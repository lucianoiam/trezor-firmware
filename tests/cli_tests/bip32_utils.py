"""
Standalone BIP32 utilities for public key derivation.
Works outside of trezor runtime using pure Python ecdsa library.
"""

try:
    from typing import Tuple
except ImportError:
    pass

import hashlib
import hmac
import struct

# Base58 alphabet
B58_CHARS = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
B58_BASE = len(B58_CHARS)


def b58decode(v: str) -> bytes:
    """Decode base58 string to bytes."""
    origlen = len(v)
    v = v.lstrip(B58_CHARS[0])
    newlen = len(v)
    decimal = 0
    for char in v:
        decimal = decimal * B58_BASE + B58_CHARS.index(char)
    result = decimal.to_bytes(origlen - newlen + (decimal.bit_length() + 7) // 8, "big")
    return result


def btc_hash(data: bytes) -> bytes:
    """Double SHA256."""
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def hash160(data: bytes) -> bytes:
    """RIPEMD160(SHA256(data))."""
    return hashlib.new("ripemd160", hashlib.sha256(data).digest()).digest()


class HDNode:
    """Minimal HD node for public key derivation."""

    def __init__(
        self,
        depth: int,
        fingerprint: int,
        child_num: int,
        chain_code: bytes,
        public_key: bytes,
    ) -> None:
        self.depth = depth
        self.fingerprint = fingerprint
        self.child_num = child_num
        self.chain_code = chain_code
        self.public_key = public_key

    def derive(self, index: int) -> "HDNode":
        """Derive child public key (non-hardened only)."""
        import ecdsa
        from ecdsa.curves import SECP256k1
        from ecdsa.ellipticcurve import INFINITY, Point
        from ecdsa.util import number_to_string, string_to_number

        if index & 0x80000000:
            raise ValueError("Hardened derivation not supported for public keys")

        # Public derivation: HMAC-SHA512(chain_code, pubkey || index)
        data = self.public_key + struct.pack(">L", index)
        I64 = hmac.new(self.chain_code, data, hashlib.sha512).digest()
        I_left = string_to_number(I64[:32])
        I_right = I64[32:]

        # Parse compressed public key to point
        x = string_to_number(self.public_key[1:33])
        prefix = self.public_key[0]
        curve = SECP256k1.curve
        p = curve.p()
        alpha = (pow(x, 3, p) + curve.a() * x + curve.b()) % p
        beta = ecdsa.numbertheory.square_root_mod_prime(alpha, p)
        if (prefix == 2) == (beta & 1):
            y = p - beta
        else:
            y = beta

        # Add I_left * G to current point
        point = I_left * SECP256k1.generator + Point(curve, x, y, SECP256k1.order)
        if point == INFINITY:
            raise ValueError("Point at infinity")

        # Compress new public key
        order = SECP256k1.order
        x_str = number_to_string(point.x(), order)
        new_pubkey = bytes([(point.y() & 1) + 2]) + x_str

        # Fingerprint of parent
        fp = struct.unpack(">I", hash160(self.public_key)[:4])[0]

        return HDNode(
            depth=self.depth + 1,
            fingerprint=fp,
            child_num=index,
            chain_code=I_right,
            public_key=new_pubkey,
        )


def deserialize_xpub(xpub: str) -> HDNode:
    """Deserialize an xpub/tpub string to HDNode."""
    data = b58decode(xpub)

    # Verify checksum
    if btc_hash(data[:-4])[:4] != data[-4:]:
        raise ValueError("Invalid checksum")

    # Parse fields
    # version = struct.unpack(">I", data[0:4])[0]  # not used
    depth = data[4]
    fingerprint = struct.unpack(">I", data[5:9])[0]
    child_num = struct.unpack(">I", data[9:13])[0]
    chain_code = data[13:45]
    key = data[45:78]

    if key[0] == 0:
        raise ValueError("Private key not supported")

    return HDNode(
        depth=depth,
        fingerprint=fingerprint,
        child_num=child_num,
        chain_code=chain_code,
        public_key=key,
    )


def derive_pubkey_from_xpub(xpub: str, path: str) -> bytes:
    """
    Derive a public key from xpub and path.

    Args:
        xpub: Extended public key (xpub or tpub)
        path: Derivation path like "0/0" or "<0;1>/0" (ranges use first value)

    Returns:
        Compressed public key bytes (33 bytes)
    """
    node = deserialize_xpub(xpub)

    if not path:
        return node.public_key

    for part in path.split("/"):
        if not part or part == "*":
            continue
        # Handle ranges like <0;1>
        if part.startswith("<") and part.endswith(">"):
            inner = part[1:-1]
            values = inner.split(";")
            part = values[0]
        if part:
            node = node.derive(int(part))

    return node.public_key
