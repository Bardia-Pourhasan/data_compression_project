from __future__ import annotations

import struct
from typing import Dict, Tuple

from .huffman import (
    bits_to_bytes,
    build_huffman_tree,
    bytes_to_bits,
    generate_codes,
)

ADAPTIVE_MAGIC = b"AHF1"
ESCAPE = 256


def _decode_one(bits: str, start: int, root) -> Tuple[int, int]:
    if root is None:
        raise ValueError("Adaptive Huffman tree is missing.")

    if root.is_leaf:
        if start >= len(bits) or bits[start] != "0":
            raise ValueError("Invalid single-node adaptive code.")
        return int(root.symbol), start + 1

    node = root
    index = start
    while not node.is_leaf:
        if index >= len(bits):
            raise ValueError("Truncated adaptive Huffman stream.")
        bit = bits[index]
        index += 1
        if bit == "0":
            node = node.left
        elif bit == "1":
            node = node.right
        else:
            raise ValueError("Invalid adaptive Huffman bit.")
        if node is None:
            raise ValueError("Invalid adaptive Huffman path.")

    return int(node.symbol), index


def compress_adaptive(data: bytes) -> bytes:
    counts: Dict[int, int] = {ESCAPE: 1}
    chunks = []

    for value in data:
        root = build_huffman_tree(counts)
        codes = generate_codes(root)

        if value in counts:
            chunks.append(codes[value])
            counts[value] += 1
        else:
            chunks.append(codes[ESCAPE])
            chunks.append(f"{value:08b}")
            counts[value] = 1

    bits = "".join(chunks)
    payload = bits_to_bytes(bits)
    return ADAPTIVE_MAGIC + struct.pack(">QQ", len(data), len(bits)) + payload


def decompress_adaptive(blob: bytes) -> bytes:
    if len(blob) < 20 or blob[:4] != ADAPTIVE_MAGIC:
        raise ValueError("Invalid adaptive Huffman file.")

    original_size, bit_length = struct.unpack_from(">QQ", blob, 4)
    bits = bytes_to_bits(blob[20:], bit_length)
    counts: Dict[int, int] = {ESCAPE: 1}
    output = bytearray()
    index = 0

    while len(output) < original_size:
        root = build_huffman_tree(counts)
        symbol, index = _decode_one(bits, index, root)

        if symbol == ESCAPE:
            if index + 8 > len(bits):
                raise ValueError("Truncated raw symbol in adaptive Huffman stream.")
            value = int(bits[index:index + 8], 2)
            index += 8
            if value in counts:
                raise ValueError("Escape code used for an existing symbol.")
            output.append(value)
            counts[value] = 1
        else:
            if symbol not in counts:
                raise ValueError("Unknown adaptive Huffman symbol.")
            output.append(symbol)
            counts[symbol] += 1

    if index > bit_length:
        raise ValueError("Adaptive Huffman stream overrun.")
    return bytes(output)
