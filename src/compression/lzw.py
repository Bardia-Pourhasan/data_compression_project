from __future__ import annotations

import struct
from typing import Dict, List

LZW_MAGIC = b"LZW1"
MAX_CODE = 4095
CODE_WIDTH = 12


def lzw_encode(data: bytes, max_code: int = MAX_CODE) -> List[int]:
    if not data:
        return []

    dictionary: Dict[bytes, int] = {bytes([value]): value for value in range(256)}
    next_code = 256
    current = bytes([data[0]])
    output: List[int] = []

    for value in data[1:]:
        candidate = current + bytes([value])
        if candidate in dictionary:
            current = candidate
        else:
            output.append(dictionary[current])
            if next_code <= max_code:
                dictionary[candidate] = next_code
                next_code += 1
            current = bytes([value])

    output.append(dictionary[current])
    return output


def lzw_decode(codes: List[int], max_code: int = MAX_CODE) -> bytes:
    if not codes:
        return b""

    dictionary: Dict[int, bytes] = {value: bytes([value]) for value in range(256)}
    next_code = 256

    first = codes[0]
    if first not in dictionary:
        raise ValueError("Invalid first LZW code.")

    current = dictionary[first]
    output = bytearray(current)

    for code in codes[1:]:
        if code in dictionary:
            entry = dictionary[code]
        elif code == next_code:
            entry = current + current[:1]
        else:
            raise ValueError(f"Invalid LZW code: {code}")

        output.extend(entry)
        if next_code <= max_code:
            dictionary[next_code] = current + entry[:1]
            next_code += 1
        current = entry

    return bytes(output)


def pack_12bit_codes(codes: List[int]) -> bytes:
    accumulator = 0
    bits_in_accumulator = 0
    payload = bytearray()

    for code in codes:
        if not 0 <= code <= MAX_CODE:
            raise ValueError("A 12-bit LZW code must be between 0 and 4095.")
        accumulator = (accumulator << CODE_WIDTH) | code
        bits_in_accumulator += CODE_WIDTH

        while bits_in_accumulator >= 8:
            bits_in_accumulator -= 8
            payload.append((accumulator >> bits_in_accumulator) & 0xFF)
            accumulator &= (1 << bits_in_accumulator) - 1 if bits_in_accumulator else 0

    if bits_in_accumulator:
        payload.append((accumulator << (8 - bits_in_accumulator)) & 0xFF)

    return bytes(payload)


def unpack_12bit_codes(payload: bytes, code_count: int) -> List[int]:
    codes: List[int] = []
    accumulator = 0
    bits_in_accumulator = 0

    for byte in payload:
        accumulator = (accumulator << 8) | byte
        bits_in_accumulator += 8

        while bits_in_accumulator >= CODE_WIDTH and len(codes) < code_count:
            bits_in_accumulator -= CODE_WIDTH
            codes.append((accumulator >> bits_in_accumulator) & MAX_CODE)
            accumulator &= (1 << bits_in_accumulator) - 1 if bits_in_accumulator else 0

    if len(codes) != code_count:
        raise ValueError("Truncated LZW payload.")
    return codes


def compress_lzw(data: bytes) -> bytes:
    codes = lzw_encode(data)
    payload = pack_12bit_codes(codes)
    return LZW_MAGIC + struct.pack(">QQ", len(data), len(codes)) + payload


def decompress_lzw(blob: bytes) -> bytes:
    if len(blob) < 20 or blob[:4] != LZW_MAGIC:
        raise ValueError("Invalid LZW file.")
    original_size, code_count = struct.unpack_from(">QQ", blob, 4)
    codes = unpack_12bit_codes(blob[20:], code_count)
    decoded = lzw_decode(codes)
    if len(decoded) != original_size:
        raise ValueError("LZW output size mismatch.")
    return decoded
