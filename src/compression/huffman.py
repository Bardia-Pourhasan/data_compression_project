from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from itertools import count
import heapq
import math
import struct
from typing import Dict, Hashable, Iterable, List, Mapping, Optional, Sequence, Tuple, TypeVar

Symbol = TypeVar("Symbol", bound=Hashable)
HUFFMAN_MAGIC = b"HUF1"


@dataclass(order=True)
class HuffmanNode:
    frequency: int
    order: int
    symbol: Optional[Hashable] = field(default=None, compare=False)
    left: Optional["HuffmanNode"] = field(default=None, compare=False)
    right: Optional["HuffmanNode"] = field(default=None, compare=False)

    @property
    def is_leaf(self) -> bool:
        return self.left is None and self.right is None


def frequency_table(data: Iterable[Symbol]) -> Dict[Symbol, int]:
    return dict(Counter(data))


def build_huffman_tree(frequencies: Mapping[Symbol, int]) -> Optional[HuffmanNode]:
    if not frequencies:
        return None

    serial = count()
    heap: List[HuffmanNode] = []
    for symbol, frequency in sorted(frequencies.items(), key=lambda item: repr(item[0])):
        if frequency <= 0:
            raise ValueError("All frequencies must be positive.")
        heapq.heappush(
            heap,
            HuffmanNode(
                frequency=int(frequency),
                order=next(serial),
                symbol=symbol,
            ),
        )

    while len(heap) > 1:
        left = heapq.heappop(heap)
        right = heapq.heappop(heap)
        parent = HuffmanNode(
            frequency=left.frequency + right.frequency,
            order=next(serial),
            left=left,
            right=right,
        )
        heapq.heappush(heap, parent)

    return heap[0]


def generate_codes(root: Optional[HuffmanNode]) -> Dict[Symbol, str]:
    if root is None:
        return {}

    codes: Dict[Symbol, str] = {}

    def visit(node: HuffmanNode, prefix: str) -> None:
        if node.is_leaf:
            codes[node.symbol] = prefix or "0"
            return
        if node.left is not None:
            visit(node.left, prefix + "0")
        if node.right is not None:
            visit(node.right, prefix + "1")

    visit(root, "")
    return codes


def encode_symbols(data: Sequence[Symbol], codes: Mapping[Symbol, str]) -> str:
    try:
        return "".join(codes[symbol] for symbol in data)
    except KeyError as exc:
        raise ValueError(f"Missing Huffman code for symbol: {exc.args[0]!r}") from exc


def decode_bits(
    bits: str,
    root: Optional[HuffmanNode],
    expected_length: Optional[int] = None,
) -> List[Symbol]:
    if root is None:
        if bits or (expected_length not in (None, 0)):
            raise ValueError("A non-empty stream cannot be decoded without a tree.")
        return []

    if root.is_leaf:
        length = expected_length if expected_length is not None else len(bits)
        if expected_length is not None and len(bits) < expected_length:
            raise ValueError("Truncated single-symbol Huffman bit stream.")
        if length < 0:
            raise ValueError("Expected length cannot be negative.")
        if bits and any(bit != "0" for bit in bits[:length]):
            raise ValueError("Invalid bit for a single-symbol Huffman tree.")
        return [root.symbol] * length

    result: List[Symbol] = []
    node = root
    for bit in bits:
        if bit == "0":
            node = node.left
        elif bit == "1":
            node = node.right
        else:
            raise ValueError("Bit stream must contain only '0' and '1'.")

        if node is None:
            raise ValueError("Invalid Huffman bit stream.")

        if node.is_leaf:
            result.append(node.symbol)
            if expected_length is not None and len(result) == expected_length:
                return result
            node = root

    if node is not root:
        raise ValueError("Truncated Huffman bit stream.")
    if expected_length is not None and len(result) != expected_length:
        raise ValueError("Decoded length does not match the expected length.")
    return result


def shannon_entropy(frequencies: Mapping[Hashable, int]) -> float:
    total = sum(frequencies.values())
    if total == 0:
        return 0.0
    return -sum(
        (frequency / total) * math.log2(frequency / total)
        for frequency in frequencies.values()
        if frequency > 0
    )


def average_code_length(
    frequencies: Mapping[Symbol, int],
    codes: Mapping[Symbol, str],
) -> float:
    total = sum(frequencies.values())
    if total == 0:
        return 0.0
    return sum(frequencies[symbol] * len(codes[symbol]) for symbol in frequencies) / total


def is_prefix_free(codes: Mapping[Hashable, str]) -> bool:
    values = list(codes.values())
    return all(
        not other.startswith(code)
        for i, code in enumerate(values)
        for j, other in enumerate(values)
        if i != j
    )


def kraft_sum(codes: Mapping[Hashable, str]) -> float:
    return sum(2.0 ** (-len(code)) for code in codes.values())


def bits_to_bytes(bits: str) -> bytes:
    if not bits:
        return b""
    padding = (-len(bits)) % 8
    padded = bits + ("0" * padding)
    return bytes(int(padded[i:i + 8], 2) for i in range(0, len(padded), 8))


def bytes_to_bits(payload: bytes, bit_length: int) -> str:
    if bit_length < 0 or bit_length > len(payload) * 8:
        raise ValueError("Invalid bit length.")
    return "".join(f"{byte:08b}" for byte in payload)[:bit_length]


def compress_bytes(data: bytes) -> bytes:
    frequencies = frequency_table(data)
    root = build_huffman_tree(frequencies)
    codes = generate_codes(root)
    bits = encode_symbols(list(data), codes)
    payload = bits_to_bytes(bits)

    header = bytearray(HUFFMAN_MAGIC)
    header.extend(struct.pack(">QH", len(data), len(frequencies)))
    for symbol, frequency in sorted(frequencies.items()):
        header.extend(struct.pack(">BQ", int(symbol), int(frequency)))
    header.extend(struct.pack(">Q", len(bits)))
    return bytes(header) + payload


def decompress_bytes(blob: bytes) -> bytes:
    if len(blob) < 22 or blob[:4] != HUFFMAN_MAGIC:
        raise ValueError("Invalid Huffman file.")

    offset = 4
    original_size, symbol_count = struct.unpack_from(">QH", blob, offset)
    offset += 10

    frequencies: Dict[int, int] = {}
    for _ in range(symbol_count):
        if offset + 9 > len(blob):
            raise ValueError("Truncated Huffman header.")
        symbol, frequency = struct.unpack_from(">BQ", blob, offset)
        offset += 9
        frequencies[symbol] = frequency

    if offset + 8 > len(blob):
        raise ValueError("Missing Huffman bit length.")
    bit_length = struct.unpack_from(">Q", blob, offset)[0]
    offset += 8

    payload = blob[offset:]
    bits = bytes_to_bits(payload, bit_length)
    root = build_huffman_tree(frequencies)
    decoded = decode_bits(bits, root, expected_length=original_size)
    result = bytes(decoded)

    if len(result) != original_size:
        raise ValueError("Huffman output size mismatch.")
    return result
