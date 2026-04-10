# SimpleLang vs Go vs Rust: Binary Comparison

What's actually inside a "Hello, World!" binary when you compile it with no runtime (SimpleLang) vs with a runtime (Go, Rust)?

## How to reproduce

```bash
# Build SimpleLang binary
python3 compiler.py hello.sl

# Build Go binary
mkdir -p /tmp/gohello
cat > /tmp/gohello/main.go << 'EOF'
package main

import "fmt"

func main() {
    fmt.Println("Hello, World!")
}
EOF
cd /tmp/gohello && go build -o hello_go main.go

# Compare sizes
ls -la hello
ls -la /tmp/gohello/hello_go

# List runtime symbols in Go binary
nm /tmp/gohello/hello_go 2>/dev/null | grep -c "runtime\."

# GC-related symbols
nm /tmp/gohello/hello_go 2>/dev/null | grep -iE "runtime.*(gc|sweep|heap|alloc|mspan|scaveng)" | wc -l

# Goroutine scheduler symbols
nm /tmp/gohello/hello_go 2>/dev/null | grep -i "runtime\." | grep -iE "sched|gopark|goready|goroutine|proc\.go|goexit"
```

## Results

### Size comparison

| Binary | Size | Ratio |
|--------|------|-------|
| SimpleLang | 16 KB | 1x |
| Rust (no_std) | ~16 KB | ~1x |
| C | ~50 KB | ~3x |
| Rust (std) | ~400 KB | ~25x |
| Go | 2.3 MB | 140x |

### What's in each binary

| | SimpleLang | Rust (no_std) | Rust (std) | Go |
|---|---|---|---|---|
| Runtime | None | None | Thin | Full |
| GC | No | No | No | Yes (309 symbols) |
| Libc | No | No | Yes | No (own syscalls) |
| Syscalls | Direct | Direct | Via libc | Direct |
| Panic handling | No | No | Yes | Yes |
| Buffered I/O | No | No | Yes | Yes |
| Total runtime symbols | 0 | 0 | ~50 | 1,657 |

## What Go ships inside every binary

Even for "Hello, World!", the Go binary contains a **full runtime** that starts before your `main()` runs:

```
┌─────────────────────────────────────────────────────┐
│                   Go Binary                         │
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │  Go Runtime (starts first, always present)   │   │
│  │                                              │   │
│  │  • Goroutine scheduler (M:N threading)       │   │
│  │    - Creates system threads                  │   │
│  │    - Manages goroutine run queues            │   │
│  │    - Work stealing between threads           │   │
│  │                                              │   │
│  │  • Garbage collector                         │   │
│  │    - Concurrent tri-color mark & sweep       │   │
│  │    - Write barriers on pointer assignments   │   │
│  │    - Background sweeper goroutines           │   │
│  │    - 309 symbols just for GC                 │   │
│  │                                              │   │
│  │  • Memory allocator                          │   │
│  │    - mspan/mcache/mcentral/mheap             │   │
│  │    - Size-class based allocation             │   │
│  │    - OS memory scavenging                    │   │
│  │                                              │   │
│  │  • Stack manager                             │   │
│  │    - Goroutines start with tiny 2KB stacks   │   │
│  │    - Grows/copies stacks as needed           │   │
│  │                                              │   │
│  │  • Netpoller, signal handlers, profiler...   │   │
│  └──────────────────────────────────────────────┘   │
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │  Your code                                   │   │
│  │  fmt.Println("Hello, World!")                │   │
│  └──────────────────────────────────────────────┘   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## The execution difference

### SimpleLang

```
_main → write syscall → exit syscall → done
```

### Go

```
_rt0_arm64_darwin (entry)
  → runtime.osinit()          ← detect CPU count, page size
  → runtime.schedinit()       ← init scheduler, GC, memory allocator
  → runtime.newproc()         ← create goroutine for main.main
  → runtime.mstart()          ← start scheduler loop
    → schedule()
      → execute(main goroutine)
        → main.main()
          → fmt.Println()
            → ... reflection, interfaces, buffered I/O ...
            → syscall write    ← SAME syscall we use!
  → runtime.exit()            ← teardown
```

All that machinery exists so Go can give you goroutines, GC, and safe memory. For "Hello, World!" it's pure overhead. For a real concurrent server — it's what makes Go powerful.

## The punchline

At the very bottom, Go's `fmt.Println` ends up at the same `write` syscall our 16KB binary uses directly. Everything above it is abstraction that enables higher-level features.

## Sample Go runtime symbols

### GC symbols (first 20 of 309)

```
_runtime.(*activeSweep).end
_runtime.(*consistentHeapStats).acquire
_runtime.(*consistentHeapStats).release
_runtime.(*fixalloc).alloc
_runtime.(*fixalloc).free
_runtime.(*fixalloc).init
_runtime.(*gcCPULimiterState).accumulate
_runtime.(*gcCPULimiterState).finishGCTransition
_runtime.(*gcCPULimiterState).resetCapacity
_runtime.(*gcCPULimiterState).startGCTransition
_runtime.(*gcCPULimiterState).update
_runtime.(*gcCPULimiterState).updateLocked
_runtime.(*gcControllerState).addIdleMarkWorker
_runtime.(*gcControllerState).commit
_runtime.(*gcControllerState).endCycle
_runtime.(*gcControllerState).enlistWorker
_runtime.(*gcControllerState).findRunnableGCWorker
_runtime.(*gcControllerState).heapGoalInternal
_runtime.(*gcControllerState).init
_runtime.(*gcControllerState).markWorkerStop
```

### Goroutine scheduler symbols (sample)

```
_runtime.Gosched
_runtime.goexit0
_runtime.goexit1
_runtime.gopark
_runtime.goroutineheader
_runtime.goschedIfBusy
_runtime.doRecordGoroutineProfile
```

## Rust comparison

### Rust std: thin runtime, no GC

Rust's standard binary includes a thin runtime — not a GC or scheduler, but:

- **`std::rt::lang_start()`** — entry point before your `main()`, sets up panic handler, signal handlers, thread-local storage
- **Panic machinery** — stack unwinding (like C++ exceptions), panic messages, formatting, backtrace support. This is the bulk of the binary size.
- **`std::io` buffered I/O** — `println!` goes through a write buffer, locks stdout for thread safety, calls libc `write()` underneath

No garbage collector. No goroutine scheduler. Memory is managed at compile time via ownership.

### Rust no_std: nearly identical to SimpleLang

With `#![no_std]` and `#![no_main]`, Rust strips everything and produces a binary almost identical to ours — tiny, no libc, raw syscalls.

But you still need one `asm!` call per syscall, because `svc #0x80` is a CPU trap instruction — no high-level language has syntax for switching privilege levels. This is a hardware boundary, not a language limitation.

### How Rust avoids needing a GC

Go needs a runtime because it has garbage collection — something must track allocations and free them at runtime. Rust solved this at **compile time** with ownership:

```
Go (runtime does it):
  obj := new(Thing)        // allocate
  // ... use obj ...
  // GC finds it's unreachable → frees it (at runtime, costs CPU)

Rust (compiler does it):
  let obj = Thing::new();  // allocate
  // ... use obj ...
  }                        // compiler inserts drop(obj) HERE (at compile time, free)
```

The compiler figures out exactly when every value dies and inserts cleanup code directly. No GC running in the background, no mark-and-sweep, no pauses.

## The universal bottom layer

Every language — SimpleLang, Rust, Go, C, Python — eventually hits the same boundary:

```
Your language
    ↓
Compiled/interpreted code
    ↓
Thin syscall wrapper (svc #0x80 on ARM64 — unavoidable)
    ↓
Kernel → hardware
```

The only question is how thick the layer between your code and that `svc` instruction is.

## The execution model spectrum

```
Pure interpreter    Bytecode + VM       JIT compiled        Ahead-of-time compiled
(bash)              (Python, Java*)     (Java HotSpot,      (C, Go, Rust,
                                         JS V8)              SimpleLang!)

source → execute    source → bytecode   bytecode → native   source → native
char by char        → C interpreter     at runtime          before execution
                      loop

Slowest             Slow                Fast                 Fastest
```

Python has **two layers** of machine code at runtime: a C interpreter loop reads bytecodes one at a time and simulates your program. Go, Rust, and SimpleLang are all in the rightmost category — the CPU executes your code directly as native machine instructions. The difference is just how much compiled code ships alongside it.
