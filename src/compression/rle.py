from __future__ import annotations


def rle_encode(data: bytes) -> bytes:
    if not data:
        return b""

    output = bytearray()
    current = data[0]
    count = 1

    for value in data[1:]:
        if value == current and count < 255:
            count += 1
        else:
            output.extend((count, current))
            current = value
            count = 1

    output.extend((count, current))
    return bytes(output)


def rle_decode(blob: bytes) -> bytes:
    if len(blob) % 2:
        raise ValueError("RLE data must contain count/value pairs.")

    output = bytearray()
    for index in range(0, len(blob), 2):
        count = blob[index]
        value = blob[index + 1]
        if count == 0:
            raise ValueError("RLE count cannot be zero.")
        output.extend([value] * count)
    return bytes(output)
