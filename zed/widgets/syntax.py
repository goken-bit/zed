from kivy.utils import escape_markup

from pygments.lexers import PythonLexer, CppLexer
from pygments.token import (
    Keyword, Name, String, Comment, Number, Operator,
    Punctuation, Generic, Error,
)

COLORS = {
    Keyword: "#C586C0",
    Keyword.Constant: "#569CD6",
    Keyword.Namespace: "#C586C0",
    Keyword.Declaration: "#C586C0",
    Keyword.Type: "#569CD6",
    Name.Function: "#DCDCAA",
    Name.Class: "#4EC9B0",
    Name.Builtin: "#DCDCAA",
    Name.Builtin.Pseudo: "#DCDCAA",
    Name.Decorator: "#DCDCAA",
    Name.Namespace: "#4EC9B0",
    Name.Attribute: "#9CDCFE",
    Name.Constant: "#569CD6",
    Name.Label: "#C586C0",
    Name.Variable: "#9CDCFE",
    Name.Variable.Class: "#9CDCFE",
    String: "#CE9178",
    String.Doc: "#6A9955",
    Comment: "#6A9955",
    Number: "#B5CEA8",
    Operator: "#D4D4D4",
    Operator.Word: "#C586C0",
    Punctuation: "#D4D4D4",
    Generic.Error: "#F14C4C",
    Error: "#F14C4C",
}

DEFAULT_COLOR = "#D4D4D4"

LEXERS = {
    ".py": PythonLexer,
    ".pyw": PythonLexer,
    ".cpp": CppLexer,
    ".cxx": CppLexer,
    ".cc": CppLexer,
    ".c": CppLexer,
    ".h": CppLexer,
    ".hpp": CppLexer,
    ".hxx": CppLexer,
    ".hh": CppLexer,
    ".ino": CppLexer,
}


def language_for(path):
    import os
    ext = os.path.splitext(path)[1].lower()
    if ext in LEXERS:
        return LEXERS[ext]
    return None


def color_for_token(tok):
    t = tok
    while t is not None:
        if t in COLORS:
            return COLORS[t]
        t = t.parent
    return DEFAULT_COLOR


def tokenize(text, lexer):
    return list(lexer().get_tokens(text))


class Highlighter:
    def __init__(self, lexer=None):
        self.lexer = lexer
        self._version = -1
        self._text = None
        self._lines = None

    def set_language(self, lexer):
        self.lexer = lexer
        self._version = -1

    def lines_for(self, text, version):
        if self._text == text and self._version == version and self._lines is not None:
            return self._lines
        self._text = text
        self._version = version
        if self.lexer is None:
            self._lines = [escape_markup(ln) for ln in text.split("\n")]
        else:
            result = []
            cur = []
            for tok, value in tokenize(text, self.lexer):
                if not value:
                    continue
                color = color_for_token(tok)
                parts = value.split("\n")
                for j, part in enumerate(parts):
                    if part:
                        cur.append("[color=%s]%s[/color]" % (color, escape_markup(part)))
                    if j < len(parts) - 1:
                        result.append("".join(cur))
                        cur = []
            result.append("".join(cur))
            self._lines = result
        return self._lines
