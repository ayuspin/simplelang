# PARSER: Tokens → AST (Abstract Syntax Tree)
#
# Takes the flat list of tokens from the lexer and builds a tree
# structure that represents *what the program means*.
#
# Grammar (the rules of our language):
#   program    = statement*
#   statement  = "print" STRING
#
# That's it! The only valid program is one or more print statements.
#
# Example:
#   [Token(KEYWORD, "print"), Token(STRING, "Hello, World!"), Token(EOF)]
#   → Program(body=[PrintStatement(value="Hello, World!")])


class PrintStatement:
    """AST node: a print command with a string to print."""
    def __init__(self, value):
        self.value = value  # The string to print

    def __repr__(self):
        return f"PrintStatement({self.value!r})"


class Program:
    """AST node: the root — contains a list of statements."""
    def __init__(self, body):
        self.body = body  # List of statements

    def __repr__(self):
        return f"Program({self.body})"


def parse(tokens):
    """Parse a list of tokens into an AST."""
    pos = 0

    def current():
        return tokens[pos]

    def eat(type, value=None):
        """Consume the current token if it matches, otherwise error."""
        nonlocal pos
        tok = tokens[pos]
        if tok.type != type or (value is not None and tok.value != value):
            raise SyntaxError(f"Expected {type} {value!r}, got {tok}")
        pos += 1
        return tok

    # Parse statements until we hit EOF
    body = []
    while current().type != "EOF":
        # The only statement we support: print "..."
        eat("KEYWORD", "print")
        string_tok = eat("STRING")
        body.append(PrintStatement(string_tok.value))

    return Program(body)


# Quick test
if __name__ == "__main__":
    from lexer import tokenize
    with open("hello.sl") as f:
        tokens = tokenize(f.read())
    print(f"Tokens: {tokens}")
    ast = parse(tokens)
    print(f"AST:    {ast}")
