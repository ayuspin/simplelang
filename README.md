# SimpleLang

A minimal compiled programming language that produces native ARM64 macOS binaries with **no runtime** — just raw syscalls to the kernel.

Built as a learning project to understand how programming languages work from the ground up.

## What It Does

This SimpleLang program:

```
print "Hello, World!"
```

Compiles to a **native ARM64 binary** that talks directly to the macOS kernel via syscalls. No libc. No runtime. No dependencies.

## How It Works

```
Source Code → [Lexer] → Tokens → [Parser] → AST → [Code Gen] → Assembly → [as + ld] → Binary
```

| Stage | File | What it does |
|-------|------|-------------|
| Lexer | `lexer.py` | Breaks source text into tokens (the "words" of the language) |
| Parser | `parser.py` | Builds an AST (tree structure) and enforces grammar rules |
| Code Gen | `codegen.py` | Walks the AST and emits ARM64 assembly using raw syscalls |
| Driver | `compiler.py` | Orchestrates the pipeline and invokes `as` + `ld` |

The generated binary uses only two syscalls:
- `write` (syscall `0x4`) — print bytes to stdout
- `exit` (syscall `0x1`) — terminate the process

## Usage

```bash
# Compile
python3 compiler.py hello.sl

# Run
./hello
Hello, World!
```

## Requirements

- macOS on Apple Silicon (ARM64)
- Python 3
- Xcode Command Line Tools (`xcode-select --install`)

## Project Structure

```
simplelang/
├── lexer.py        # Stage 1: text → tokens
├── parser.py       # Stage 2: tokens → AST
├── codegen.py      # Stage 3: AST → ARM64 assembly
├── compiler.py     # Compiler driver (glues stages + invokes as/ld)
└── hello.sl        # Example SimpleLang program
```

## The Generated Assembly

For `print "Hello, World!"`, the compiler generates:

```asm
.section __TEXT,__cstring
str_0: .ascii "Hello, World!\n"

.section __TEXT,__text
.global _main
.align 2
_main:
    mov x0, #1              ; fd = stdout
    adrp x1, str_0@PAGE     ; pointer to string
    add x1, x1, str_0@PAGEOFF
    mov x2, #14             ; length
    mov x16, #4             ; syscall: write
    svc #0x80               ; call kernel

    mov x0, #0              ; exit code 0
    mov x16, #1             ; syscall: exit
    svc #0x80               ; call kernel
```

No magic. Every instruction has a purpose.
