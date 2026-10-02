from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Iterator


class TokenKind(enum.Enum):
    """Interface publicada na etapa do lexer; nomes e números são fixos."""

    EOF = -1
    IDENTIFIER = 1
    INT_LITERAL = 2
    STRING_LITERAL = 3
    KW_INT = 10
    KW_BOOL = 11
    KW_VOID = 12
    KW_TRUE = 13
    KW_FALSE = 14
    KW_IF = 15
    KW_ELSE = 16
    KW_WHILE = 17
    KW_RETURN = 18
    KW_PRINT = 19
    PLUS = 20
    MINUS = 21
    STAR = 22
    SLASH = 23
    PERCENT = 24
    LESS = 25
    LESS_EQUAL = 26
    GREATER = 27
    GREATER_EQUAL = 28
    EQUAL_EQUAL = 29
    NOT_EQUAL = 30
    LOGICAL_AND = 31
    LOGICAL_OR = 32
    LOGICAL_NOT = 33
    ASSIGN = 34
    LEFT_PAREN = 40
    RIGHT_PAREN = 41
    LEFT_BRACE = 42
    RIGHT_BRACE = 43
    COMMA = 44
    SEMICOLON = 45


@dataclass(frozen=True)
class Token:
    kind: TokenKind
    lexeme: str
    value: int | str | bool | None
    line: int
    column: int

    def __str__(self) -> str:
        return (
            f"<{self.kind.value}, {self.kind.name}, {self.lexeme!r}, "
            f"{self.value!r}, {self.line}, {self.column}>"
        )


class LexerError(Exception):
    def __init__(self, message: str, line: int, column: int):
        super().__init__(message)
        self.message = message
        self.line = line
        self.column = column

    def __str__(self) -> str:
        return f"erro léxico em {self.line}:{self.column}: {self.message}"


class Lexer:
    KEYWORDS = {
        "int": TokenKind.KW_INT, "bool": TokenKind.KW_BOOL, "void": TokenKind.KW_VOID,
        "true": TokenKind.KW_TRUE, "false": TokenKind.KW_FALSE, "if": TokenKind.KW_IF,
        "else": TokenKind.KW_ELSE, "while": TokenKind.KW_WHILE, "return": TokenKind.KW_RETURN,
        "print": TokenKind.KW_PRINT
    }

    COMPOUND_OPS = {
        '=': ('=', TokenKind.EQUAL_EQUAL, TokenKind.ASSIGN),
        '!': ('=', TokenKind.NOT_EQUAL, TokenKind.LOGICAL_NOT),
        '<': ('=', TokenKind.LESS_EQUAL, TokenKind.LESS),
        '>': ('=', TokenKind.GREATER_EQUAL, TokenKind.GREATER),
        '&': ('&', TokenKind.LOGICAL_AND, None),
        '|': ('|', TokenKind.LOGICAL_OR, None)
    }

    SINGLE_OPS = {
        '+': TokenKind.PLUS, '-': TokenKind.MINUS, '*': TokenKind.STAR,
        '/': TokenKind.SLASH, '%': TokenKind.PERCENT, '(': TokenKind.LEFT_PAREN,
        ')': TokenKind.RIGHT_PAREN, '{': TokenKind.LEFT_BRACE, '}': TokenKind.RIGHT_BRACE,
        ',': TokenKind.COMMA, ';': TokenKind.SEMICOLON
    }

    def __init__(self, source: str):
        self.source = source
        self.pos = 0
        self.line = 1
        self.column = 1
        self.length = len(source)

    def is_at_end(self) -> bool:
        return self.pos >= self.length

    def peek(self, offset = 0) -> str:
        if self.pos + offset >= self.length:
            return "\0"
        return self.source[self.pos + offset]

    def advance(self) -> str:
        if self.is_at_end():
            return "\0"
        char = self.source[self.pos]
        if ord(char) > 127:
            raise LexerError("caractere nao ASCII", self.line, self.column)
        self.pos += 1
        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char

    def skip_whitespace_and_comments(self):
        while not self.is_at_end():
            char = self.peek()
            next_char = self.peek(1)
            if char in (' ', '\t', '\r', '\n'):
                self.advance()
            elif char == '/' and next_char == '/':
                # Comentário de linha
                while not self.is_at_end() and self.peek() != '\n':
                    self.advance()
            elif char == '/' and next_char == '*':
                start_line, start_col = self.line, self.column
                self.advance() 
                self.advance() 
                
                while not (self.peek() == '*' and self.peek(1) == '/'):
                    if self.is_at_end():
                        raise LexerError("comentario de bloco nao terminado", start_line, start_col)
                    self.advance()
                
                self.advance() 
                self.advance()
            else:
                break
    
    def scan_identifier_or_keyword(self) -> Token:
        start_line, start_col = self.line, self.column
        lexeme_chars = []
        
        while self.peek().isalnum() or self.peek() == '_':
            lexeme_chars.append(self.advance())
            
        lex_str = "".join(lexeme_chars)
        
        if lex_str in self.KEYWORDS:
            kind = self.KEYWORDS[lex_str]
            val = True if lex_str == "true" else False if lex_str == "false" else None
            return Token(kind, lex_str, val, start_line, start_col)
            
        return Token(TokenKind.IDENTIFIER, lex_str, lex_str, start_line, start_col)

    def scan_number(self) -> Token:
        start_line, start_col = self.line, self.column
        lexeme_chars = []
        
        while self.peek().isdigit():
            lexeme_chars.append(self.advance())
            
        lex_str = "".join(lexeme_chars)
        return Token(TokenKind.INT_LITERAL, lex_str, int(lex_str), start_line, start_col)
    
    def scan_operator_and_punctuation(self) -> Token:
        start_line, start_col = self.line, self.column
        char = self.advance()
        next_char = self.peek()

        if char in self.COMPOUND_OPS:
            expected, kind_of_match, kind_if_not = self.COMPOUND_OPS[char]
            if next_char == expected:
                self.advance()
                return Token(kind_of_match, char + expected, None, start_line, start_col)
            if kind_if_not:
                return Token(kind_if_not, char, None, start_line, start_col)

            raise LexerError(f"caractere invalido", start_line, start_col)

        if char in self.SINGLE_OPS:
            return Token(self.SINGLE_OPS[char], char, None, start_line, start_col)

        raise LexerError(f"caractere invalido", start_line, start_col)

    # --- SEU CÓDIGO: NOVO MÉTODO NA CLASSE ---
    def scan_string(self) -> Token:
        start_line, start_col = self.line, self.column
        self.advance() # Consome a aspa dupla inicial
        
        value_chars = []
        lexeme_chars = ['"']
        
        while self.peek() != '"':
            if self.is_at_end():
                raise LexerError("string nao terminada", start_line, start_col)
            
            char = self.peek()
            if char == '\n':
                raise LexerError("quebra de linha em string", self.line, self.column)
                
            char = self.advance()
            lexeme_chars.append(char)
            
            if char == '\\':
                escape = self.advance()
                lexeme_chars.append(escape)
                if escape == 'n': value_chars.append('\n')
                elif escape == 't': value_chars.append('\t')
                elif escape == '"': value_chars.append('"')
                elif escape == '\\': value_chars.append('\\')
                else:
                    raise LexerError("escape invalido", self.line, self.column - 2)
            else:
                value_chars.append(char)
                
        self.advance() # Consome a aspa dupla final
        lexeme_chars.append('"')
        
        return Token(TokenKind.STRING_LITERAL, "".join(lexeme_chars), "".join(value_chars), start_line, start_col)

    def tokens(self) -> Iterator[Token]:
        """Produza todos os tokens significativos e um único EOF ao final."""
        while not self.is_at_end():
            self.skip_whitespace_and_comments()
            if self.is_at_end():
                break

            char = self.peek()

            if char.isalpha() or char == '_':
                yield self.scan_identifier_or_keyword()
            elif char.isdigit():
                yield self.scan_number()
            elif char == '"':
                yield self.scan_string()
            else:
                yield self.scan_operator_and_punctuation()

        yield Token(TokenKind.EOF, "", None, self.line, self.column)

    def scan(self) -> list[Token]:
        return list(self.tokens())

