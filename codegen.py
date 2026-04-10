# CODE GENERATOR: AST → ARM64 macOS Assembly
#
# Walks the AST and emits assembly instructions for each node.
# This is where high-level "print" becomes raw CPU instructions
# that talk directly to the macOS kernel.
#
# Key concepts:
#   - Syscalls: how ANY program talks to the OS (even C uses these under the hood)
#   - write(fd, buf, len) = syscall 0x2000004 → prints bytes to a file descriptor
#   - exit(code)          = syscall 0x2000001 → terminates the process
#   - On ARM64 macOS: put syscall number in x16, args in x0-x2, then "svc #0x80"


from parser import PrintStatement


def generate(ast):
    """Generate ARM64 macOS assembly from an AST."""

    # We collect string data separately (goes in .cstring section)
    strings = []   # list of (label, text)
    code = []      # assembly instructions

    # --- Data section: store our string literals ---
    # We'll build this after walking the AST

    # --- Code section: the actual instructions ---
    code.append(".global _main")
    code.append(".align 2")
    code.append("_main:")

    for i, stmt in enumerate(ast.body):
        if isinstance(stmt, PrintStatement):
            label = f"str_{i}"
            text = stmt.value
            strings.append((label, text))

            # write(1, string_ptr, length)
            #   x0 = file descriptor (1 = stdout)
            #   x1 = pointer to string data
            #   x2 = number of bytes to write
            #   x16 = syscall number
            #   svc #0x80 = "supervisor call" — triggers the kernel
            code.append(f"    // print \"{text}\"")
            code.append(f"    mov x0, #1")                  # stdout
            code.append(f"    adrp x1, {label}@PAGE")       # load string address (page)
            code.append(f"    add x1, x1, {label}@PAGEOFF") # + offset within page
            code.append(f"    mov x2, #{len(text) + 1}")    # length (+1 for newline)
            code.append(f"    mov x16, #4")                 # syscall: write
            code.append(f"    svc #0x80")                   # call kernel!

    # exit(0) — clean termination
    code.append("    // exit(0)")
    code.append("    mov x0, #0")       # exit code 0 = success
    code.append("    mov x16, #1")      # syscall: exit
    code.append("    svc #0x80")        # call kernel!

    # --- Combine data + code into final assembly ---
    lines = []

    # String data section
    lines.append(".section __TEXT,__cstring")
    for label, text in strings:
        # .asciz would add a null terminator, but we want a newline instead
        lines.append(f'{label}: .ascii "{text}\\n"')

    lines.append("")

    # Code section
    lines.append(".section __TEXT,__text")
    lines.extend(code)
    lines.append("")

    return "\n".join(lines)


# Quick test
if __name__ == "__main__":
    from lexer import tokenize
    from parser import parse
    with open("hello.sl") as f:
        ast = parse(tokenize(f.read()))
    asm = generate(ast)
    print("Generated assembly:")
    print("---")
    print(asm)
