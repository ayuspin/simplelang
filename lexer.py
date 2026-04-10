# LEXER: Raw text → Tokens
#
# Reads source code character by character and groups them into
# meaningful chunks called "tokens". This is how every language
# first "reads" your code.
#
# Example:
#   print "Hello, World!"
#   → [Token(KEYWORD, "print"), Token(STRING, "Hello, World!")]


class Token:
    """A single meaningful chunk of source code."""
    def __init__(self, type, value):
        self.type = type    # What kind of token: KEYWORD, STRING, EOF
        self.value = value  # The actual text content

    def __repr__(self):
        return f"Token({self.type}, {self.value!r})"


def tokenize(source):
    """Turn raw source code string into a list of tokens."""
    tokens = []
    i = 0

    while i < len(source):
        char = source[i]

        # Skip whitespace and newlines — they're not meaningful
        if char in ' \t\n\r':
            i += 1
            continue

        # String literal: starts with ", grab everything until closing "
        if char == '"':
            i += 1  # skip opening quote
            start = i
            while i < len(source) and source[i] != '"':
                i += 1
            if i >= len(source):
                raise SyntaxError("Unterminated string — missing closing quote")
            tokens.append(Token("STRING", source[start:i]))
            i += 1  # skip closing quote
            continue

        # Word: letters/underscores grouped together (for keywords like "print")
        if char.isalpha() or char == '_':
            start = i
            while i < len(source) and (source[i].isalpha() or source[i] == '_'):
                i += 1
            word = source[start:i]
            tokens.append(Token("KEYWORD", word))
            continue

        raise SyntaxError(f"Unexpected character: {char!r}")

    # EOF token marks the end — the parser uses this to know when to stop
    tokens.append(Token("EOF", None))
    return tokens


# Quick test: run this file directly to see tokenization in action
if __name__ == "__main__":
    with open("hello.sl") as f:
        source = f.read()
    print(f"Source: {source.strip()!r}")
    print(f"Tokens: {tokenize(source)}")
