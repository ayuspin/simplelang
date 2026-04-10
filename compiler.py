#!/usr/bin/env python3
# COMPILER DRIVER: Ties lexer → parser → codegen → assembler → linker
#
# Usage: python3 compiler.py hello.sl
# Output: ./hello (native ARM64 binary, no runtime, raw syscalls)

import sys
import subprocess
import os
from lexer import tokenize
from parser import parse
from codegen import generate


def compile(source_file):
    # Derive output names from source file
    name = os.path.splitext(os.path.basename(source_file))[0]
    asm_file = f"{name}.s"
    obj_file = f"{name}.o"
    bin_file = f"{name}"

    # --- Stage 1: Read source ---
    with open(source_file) as f:
        source = f.read()
    print(f"[1/5] Read {source_file} ({len(source)} bytes)")

    # --- Stage 2: Lex ---
    tokens = tokenize(source)
    print(f"[2/5] Lexed → {len(tokens)} tokens")

    # --- Stage 3: Parse ---
    ast = parse(tokens)
    print(f"[3/5] Parsed → {len(ast.body)} statement(s)")

    # --- Stage 4: Generate assembly ---
    asm = generate(ast)
    with open(asm_file, 'w') as f:
        f.write(asm)
    print(f"[4/5] Generated → {asm_file}")

    # --- Stage 5: Assemble + Link ---
    # as: assembly → object file (machine code, not yet executable)
    # ld: object file → executable (resolves addresses, creates Mach-O binary)
    subprocess.run(["as", "-o", obj_file, asm_file], check=True)
    subprocess.run([
        "ld", "-o", bin_file, obj_file,
        "-l", "System",           # needed for macOS to find the entry point
        "-syslibroot", "/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk",
        "-e", "_main",            # entry point is our _main label
    ], check=True)

    # Clean up intermediate files
    os.remove(obj_file)

    print(f"[5/5] Linked → ./{bin_file}")
    print(f"\nDone! Run with: ./{bin_file}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 compiler.py <file.sl>")
        sys.exit(1)
    compile(sys.argv[1])
