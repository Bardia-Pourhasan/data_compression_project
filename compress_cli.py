from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from compression import (
    compress_bytes,
    compress_lzw,
    decompress_bytes,
    decompress_lzw,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Huffman and LZW file compressor.")
    parser.add_argument("mode", choices=["huffman-compress", "huffman-decompress", "lzw-compress", "lzw-decompress"])
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    payload = args.input.read_bytes()
    operations = {
        "huffman-compress": compress_bytes,
        "huffman-decompress": decompress_bytes,
        "lzw-compress": compress_lzw,
        "lzw-decompress": decompress_lzw,
    }
    result = operations[args.mode](payload)
    args.output.write_bytes(result)
    print(f"Wrote {len(result):,} bytes to {args.output}")


if __name__ == "__main__":
    main()
