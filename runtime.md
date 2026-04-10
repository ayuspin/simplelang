# What Is a Runtime, Really?

Notes from building SimpleLang — understanding when and why a language needs a runtime.

## The short answer

A runtime is **code that the language ships in your binary that your code didn't write but depends on to work**. It's not a VM. It's not an interpreter. It's just compiled functions the compiler silently links in and calls on your behalf.

## What different languages ship

```
SimpleLang       → nothing (raw syscalls, you see everything)
C (bare)         → nothing
C (normal)       → crt0 (entry point setup, argc/argv, stdio init)
Rust (no_std)    → nothing
Rust (std)       → panic handling, buffered I/O, signal handlers
Go               → GC + goroutine scheduler + memory allocator + stack manager
Python           → entire interpreter loop + GC + import system + ...
```

## C's hidden runtime

When you write `int main()`, the OS doesn't actually call your `main()`:

```
OS loads binary → _start (crt0.o) → __libc_start_main() → your main() → exit()
                  ^^^^^^^^^^^^^^^^   ^^^^^^^^^^^^^^^^^^
                  You didn't write these. Linked in automatically.
```

What crt0 does:
- `_start` — the true entry point the OS jumps to
- Sets up the stack pointer
- Parses argc, argv, envp
- Initializes stdio (stdin/stdout/stderr FILE* structs)
- Registers atexit() cleanup handlers
- Calls your `main()`
- Calls `exit()` with main's return value

The compiler silently links this in. You never see it.

Also: `write()` in C is NOT a syscall. It's a **libc wrapper function** that sets errno, checks return values, then does the actual `svc #0x80`. Our SimpleLang skips this entirely.

## Features that DON'T need a runtime

These can all be resolved at compile time — the compiler just emits more/different assembly.

```
Feature              What the compiler does                   Runtime needed?
─────────────────    ──────────────────────────────────────   ──────────────
print "hello"        emit write syscall with string literal   ✗
variables            assign registers or stack slots          ✗
math (x + y * 2)    emit add/mul instructions                ✗
if/else              emit cmp + branch instructions           ✗
loops                emit branch-back instructions            ✗
functions            emit bl/ret (call/return)                ✗
structs              calculate field offsets, stack layout     ✗
arrays (fixed size)  stack allocation, offset math            ✗
pointers             emit load/store with addresses           ✗
print integers       emit int→string conversion code          ✗
```

SimpleLang could grow to support all of these with zero runtime. The compiler gets more complex, but the binary stays lean.

## The tipping point: dynamic memory

The moment you need heap allocation — memory whose size or lifetime isn't known at compile time — you need an allocator:

```
let name = input()     // how many bytes? unknown until the program runs
let list = []          // grows dynamically
let s = a + b          // result length unknown at compile time
```

The stack is automatic (push on function entry, pop on return, compiler knows when). The heap is a shared pool that needs management: which blocks are free, where to put new allocations, when to free, how to avoid fragmentation.

### But does the allocator = runtime?

**No — not necessarily.** This is the key insight.

```
Standard library (opt-in)         Runtime (forced)
─────────────────────────         ────────────────
You call it if you want           Compiler inserts calls automatically
Can be replaced or skipped        Can't compile without it
C's malloc, Rust's std            Go's GC, Java's GC
                                  Python's refcount on every assignment
```

If SimpleLang provides `alloc`/`free` as callable functions, that's a **library** — same as C's malloc. The user decides when to allocate and free. No runtime needed.

It only becomes a **runtime** when the language takes control away from the user and manages things implicitly — when the compiler inserts calls to memory management code whether you asked for it or not.

## Progression into runtime territory

### Level 0: No allocator (SimpleLang today)
Everything on the stack or in static data. No heap. No runtime.

### Level 1: Allocator as a library (~50 lines)
**Trigger:** dynamic strings, arrays, user input.

```
let buf = alloc(100)   // user explicitly allocates
// ... use buf ...
free(buf)              // user explicitly frees
```

This is just a library function. It asks the OS for pages via `mmap` syscall, carves them into blocks, tracks what's free. **NOT a runtime** — user is in control.

### Level 2: Automatic cleanup — this is where runtime starts

**Option A: Reference counting** (Swift, Python, Objective-C)

```
let a = Thing()          // refcount = 1
let b = a                // refcount = 2
// b goes out of scope   // refcount = 1
// a goes out of scope   // refcount = 0 → free!
```

The *compiler* inserts increment/decrement on every assignment. You didn't ask for it. You can't opt out. **This is a runtime** — small, but it's there. Downside: can't handle cycles (A → B → A leaks forever).

**Option B: Ownership** (Rust)

```
let a = Thing()
// ... use a ...
}   // compiler inserts drop(a) here — determined at compile time
```

No runtime needed! But the compiler needs complex analysis (borrow checker). Compiler complexity cost is enormous, runtime cost is zero.

**Option C: Garbage collector** (Go, Java, C#, Python)

```
func make_stuff() {
    let a = Thing()
    let b = Thing()
    return a          // b is garbage — GC will find and free it
}
// user never calls free, GC handles it
```

Now your runtime needs to:
- Track all allocations (object graph)
- Periodically walk the graph to find unreachable objects
- Free them
- Optionally compact memory to avoid fragmentation

This is the biggest runtime component in most languages (~1000+ lines). Go has 309 GC-related symbols in a hello world binary.

### Level 3: Concurrency runtime (~2000+ lines)
**Trigger:** green threads, goroutines, async/await.

```
spawn { do_work() }
spawn { do_other_work() }
```

Now your runtime needs a **scheduler**:
- Create/destroy green threads
- Context switching (save/restore registers + stack)
- Run queue management
- I/O polling (epoll/kqueue)
- Work stealing between CPU cores

This is the other big piece Go ships.

## The fundamental rule

**A runtime becomes unavoidable when the language itself — not the user — decides when to allocate, free, schedule, or manage things.**

If the user is in control (calling alloc/free explicitly), that's a library. If the compiler inserts management code on your behalf that you can't opt out of, that's a runtime.

```
User in control          Language in control
(library)                (runtime)
────────────────         ──────────────────
C: malloc/free           Go: GC frees for you
Rust: ownership          Java: GC frees for you
SimpleLang: alloc/free   Python: refcount on every assignment
                         Go: goroutine scheduler
                         Erlang: process scheduler
```

SimpleLang today has no runtime. It could add variables, math, if/else, loops, functions, structs, fixed arrays, and an allocator-as-library — all without a runtime. The line is crossed when the language starts managing things behind the user's back.
