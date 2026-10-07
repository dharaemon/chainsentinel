"""Pure-Python Keccak-256 (Ethereum's hash) — no dependencies.

Used to compute function selectors and ABI-related hashes so the keeper can
build calldata without web3/eth-utils. Verified against known vectors in the
tests (empty string, and the transfer(address,uint256) selector).
"""

from __future__ import annotations

_MASK = (1 << 64) - 1

_RC = [
    0x0000000000000001, 0x0000000000008082, 0x800000000000808A, 0x8000000080008000,
    0x000000000000808B, 0x0000000080000001, 0x8000000080008081, 0x8000000000008009,
    0x000000000000008A, 0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
    0x000000008000808B, 0x800000000000008B, 0x8000000000008089, 0x8000000000008003,
    0x8000000000008002, 0x8000000000000080, 0x000000000000800A, 0x800000008000000A,
    0x8000000080008081, 0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
]
_ROTC = [1, 3, 6, 10, 15, 21, 28, 36, 45, 55, 2, 14, 27, 41, 56, 8, 25, 43, 62, 18, 39, 61, 20, 44]
_PILN = [10, 7, 11, 17, 18, 3, 5, 16, 8, 21, 24, 4, 15, 23, 19, 13, 12, 2, 20, 14, 22, 9, 6, 1]


def _rotl(x: int, n: int) -> int:
    return ((x << n) | (x >> (64 - n))) & _MASK


def _keccak_f(st: list[int]) -> None:
    for rnd in range(24):
        # theta
        bc = [st[i] ^ st[i + 5] ^ st[i + 10] ^ st[i + 15] ^ st[i + 20] for i in range(5)]
        for i in range(5):
            t = bc[(i + 4) % 5] ^ _rotl(bc[(i + 1) % 5], 1)
            for j in range(0, 25, 5):
                st[j + i] ^= t
        # rho + pi
        t = st[1]
        for i in range(24):
            j = _PILN[i]
            prev = st[j]
            st[j] = _rotl(t, _ROTC[i])
            t = prev
        # chi
        for j in range(0, 25, 5):
            row = [st[j + i] for i in range(5)]
            for i in range(5):
                st[j + i] = (row[i] ^ ((~row[(i + 1) % 5]) & row[(i + 2) % 5])) & _MASK
        # iota
        st[0] ^= _RC[rnd]


def keccak256(data: bytes) -> bytes:
    rate = 136  # bytes (1088 bits) for Keccak-256
    pad_len = rate - (len(data) % rate)
    padded = bytearray(data) + bytearray(pad_len)
    padded[len(data)] = 0x01
    padded[-1] |= 0x80

    st = [0] * 25
    for off in range(0, len(padded), rate):
        block = padded[off:off + rate]
        for i in range(rate // 8):
            st[i] ^= int.from_bytes(block[8 * i:8 * i + 8], "little")
        _keccak_f(st)

    out = bytearray()
    for i in range(4):  # 4 lanes * 8 bytes = 32-byte digest
        out += st[i].to_bytes(8, "little")
    return bytes(out)


def selector(signature: str) -> bytes:
    """First 4 bytes of keccak256 of a canonical function signature."""
    return keccak256(signature.encode())[:4]
