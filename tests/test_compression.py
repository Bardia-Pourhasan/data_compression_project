from pathlib import Path
import os
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from compression import (
    average_code_length,
    build_huffman_tree,
    compress_adaptive,
    compress_bytes,
    compress_lzw,
    decode_bits,
    decompress_adaptive,
    decompress_bytes,
    decompress_lzw,
    encode_symbols,
    frequency_table,
    generate_codes,
    is_prefix_free,
    kraft_sum,
    rle_decode,
    rle_encode,
    shannon_entropy,
)


class CompressionTests(unittest.TestCase):
    def test_huffman_round_trip_edge_cases(self):
        cases = [
            b"",
            b"A",
            b"A" * 1000,
            b"ABRACADABRA",
            bytes(range(256)),
            bytes(random.Random(7).randrange(256) for _ in range(4096)),
        ]
        for data in cases:
            self.assertEqual(decompress_bytes(compress_bytes(data)), data)

    def test_huffman_properties(self):
        data = b"this is a deterministic huffman property test"
        frequencies = frequency_table(data)
        root = build_huffman_tree(frequencies)
        codes = generate_codes(root)
        bits = encode_symbols(list(data), codes)
        decoded = bytes(decode_bits(bits, root, expected_length=len(data)))
        entropy = shannon_entropy(frequencies)
        average = average_code_length(frequencies, codes)

        self.assertEqual(decoded, data)
        self.assertTrue(is_prefix_free(codes))
        self.assertLessEqual(kraft_sum(codes), 1.0 + 1e-12)
        self.assertLessEqual(entropy, average + 1e-12)
        self.assertLess(average, entropy + 1.0 + 1e-12)

    def test_lzw_round_trip(self):
        cases = [
            b"",
            b"A",
            b"TOBEORNOTTOBEORTOBEORNOT",
            bytes(range(256)) * 5,
            os.urandom(4096),
        ]
        for data in cases:
            self.assertEqual(decompress_lzw(compress_lzw(data)), data)

    def test_adaptive_huffman_round_trip(self):
        cases = [
            b"",
            b"A",
            b"BANANA_BANDANA",
            bytes(range(64)) * 4,
        ]
        for data in cases:
            self.assertEqual(decompress_adaptive(compress_adaptive(data)), data)

    def test_rle_round_trip(self):
        cases = [b"", b"A", b"A" * 600, b"AAABBBBBCCCCDD", bytes(range(100))]
        for data in cases:
            self.assertEqual(rle_decode(rle_encode(data)), data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
