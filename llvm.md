# LLVM and Clang

## LLVM (Low Level Virtual Machine)

LLVM is a **compiler infrastructure** — a big toolkit for building compilers. Think of it as a modular system with three layers:

1. **Frontend** — Parses a language into an intermediate representation (IR)
2. **Middle (Optimizer)** — Optimizes that IR (make code faster, smaller)
3. **Backend** — Turns optimized IR into machine code for a specific CPU (ARM64, x86, RISC-V, etc.)

The key idea: **LLVM IR** is a universal intermediate language. Any frontend can target it, and LLVM handles optimization + machine code generation for you.

```
Your language ──→ LLVM IR ──→ [LLVM Optimizer] ──→ [LLVM Backend] ──→ ARM64/x86/etc.
```

## Clang

Clang is just **one frontend** for LLVM — specifically the C/C++/Objective-C frontend. It's Apple's default C compiler (replaced GCC years ago).

```
C code ──→ [Clang frontend] ──→ LLVM IR ──→ [LLVM] ──→ machine code
Swift  ──→ [Swift frontend]  ──→ LLVM IR ──→ [LLVM] ──→ machine code
Rust   ──→ [Rust frontend]   ──→ LLVM IR ──→ [LLVM] ──→ machine code
```

## How This Relates to SimpleLang

Right now our pipeline looks like:

```
hello.sl → [our Python compiler] → ARM64 assembly (.s) → [as] → object file → [ld] → binary
```

We're doing everything ourselves — writing raw ARM64 assembly. That's great for learning, but it means:
- We're locked to ARM64 macOS
- We have to manually handle register allocation, instruction selection, etc.
- No optimizations

If we targeted **LLVM IR** instead of raw assembly, LLVM would:
- **Optimize** our code automatically
- **Generate machine code** for any supported CPU
- Handle the hard stuff (register allocation, instruction scheduling, etc.)

Our pipeline would become:
```
hello.sl → [our Python compiler] → LLVM IR → [LLVM] → native binary (any platform)
```

That said, what we're doing now (raw syscalls, hand-written assembly) teaches us **way more** about what's actually happening at the bottom of the stack. LLVM is something you'd reach for when you want to build a "real" language that needs optimization and portability.
