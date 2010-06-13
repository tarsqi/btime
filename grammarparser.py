"""A parser for Yacc-like grammar specifications."""

__author__ = "Alex Plotnick <plotnick@cs.brandeis.edu>"

from StringIO import StringIO
from tokenize import *
from tokenize import TokenError

from cfg import *
from earley import Parser

__all__ = ["parse_grammar_spec"]

EXPR = N_TOKENS
LIST = N_TOKENS + 1
TUPLE = N_TOKENS + 2
N_TOKENS += 3
tok_name[EXPR] = "EXPR"
tok_name[LIST] = "LIST"
tok_name[TUPLE] = "TUPLE"

class PyTok(Terminal):
    def __init__(self, type, value=None):
        self.type = type
        self.value = value

    def match(self, token):
        return (isinstance(token, tuple) and len(token) >= 2 and
                self.type == token[0] and
                (self.value == token[1] if self.value is not None else True))

    def __str__(self):
        if self.value:
            return "(%s, %s)" % (tok_name[self.type], self.value)
        else:
            return "%s" % tok_name[self.type]

class GrammarSpecTokenizer(object):
    delimiters = {"(":")", "[":"]", "{":"}"}
    delimtypes = {"{": EXPR, "[": LIST, "(": TUPLE}

    def __init__(self, obj):
        if isinstance(obj, basestring):
            readline = StringIO(obj).readline
        else:
            readline = obj
        self.generator = generate_tokens(readline)
        self.delimstack = []

    def __iter__(self):
        return self

    def next(self):
        def getnext():
            token = self.generator.next()
            type, value = token[:2]
            if type in (INDENT, DEDENT, NL, COMMENT):
                return getnext() # don't care
            elif type == OP:
                if value in "([{":
                    self.delimstack.append(self.delimiters[value])
                elif value in "}])":
                    if self.delimstack.pop() != value:
                        raise TokenError("improperly nested delimiters")
            return token

        def getdelimitedtoks(delimiter):
            yield delimiter[:2]
            while self.delimstack:
                yield getnext()[:2]

        token = getnext()
        if self.delimstack:
            return (self.delimtypes[token[1]],
                    untokenize(tuple(getdelimitedtoks(token))))
        else:
            return token

class InvalidActionError(Exception):
    pass

def compile_action(expr):
    if not (isinstance(expr, basestring) and
            GrammarSpecTokenizer.delimiters.get(expr[0]) == expr[-1]):
        raise InvalidActionError("invalid action expression '%s'" % expr)
    try:
        # We first assume expr is a single Python expression, and use it as
        # the body of a lambda.
        return eval(compile("lambda _: %s" % expr[1:-1], "<action>", "eval"))
    except SyntaxError:
        # Well, it's not an expression (or at least not a valid one);
        # we'll assume it's a statement suite, and use it as the body of
        # a function definition.
        namespace = {}
        exec compile("def action(_): %s" % expr[1:-1], "<action>", "exec") in \
            globals(), namespace
        return namespace["action"]

grammar_spec_grammar = AttributeGrammar([
      (Production("grammar", ("prodlist", PyTok(ENDMARKER))),
       lambda rhs: rhs[0] if isinstance(rhs[0], list) else [rhs[0]]),
      (Production("prodlist", ("prodlist", "prod", PyTok(NEWLINE))),
       lambda rhs: rhs[0] + rhs[1]),
      (Production("prodlist", ("prod", PyTok(NEWLINE)))),
      (Production("prod", (PyTok(NAME), PyTok(OP, '-'), PyTok(OP, '>'), "alt")),
       lambda rhs: [(Production(rhs[0][1], alt_rhs), action)
                    for (alt_rhs, action) in rhs[-1]]),
      (Production("alt", ("alt", PyTok(OP, '|'), "rhs")),
       lambda rhs: rhs[0] + [rhs[-1]]),
      (Production("alt", ("alt", PyTok(NEWLINE),
                          PyTok(OP, '|'), "rhs")),
       lambda rhs: rhs[0] + [rhs[-1]]),
      (Production("alt", ("rhs")),
       lambda rhs: [rhs[0]]),
      (Production("rhs", ("symlist", "action")),
       lambda rhs: tuple(rhs)),
      (Production("rhs", ("symlist")),
       lambda rhs: (rhs[0], default_action)),
      (Production("symlist", ("symlist", "sym")),
       lambda rhs: rhs[0] + [rhs[1]]),
      (Production("symlist", ("sym")),
       lambda rhs: [rhs[0]]),
      (Production("sym", PyTok(NAME)), # nonterminal
       lambda rhs: rhs[0][1]),
      (Production("sym", PyTok(STRING)), # literal
       lambda rhs: Literal(eval(rhs[0][1]))),
      (Production("sym", (PyTok(NAME), PyTok(TUPLE))), # funcall
       lambda rhs: eval(rhs[0][1] + rhs[1][1])),
      (Production("action", PyTok(EXPR)),
       lambda rhs: compile_action(rhs[0][1]))],
    start="grammar")

def parse_grammar_spec(spec, start,
                       grammar_class=AttributeGrammar,
                       parser=Parser(grammar_spec_grammar)):
    """Given a grammar specification and a start symbol, return a new grammar
    instance. The specification may be either a string or a readline-like
    function."""
    assert issubclass(grammar_class, AttributeGrammar), \
        "Grammar class must be a subclass of AttributeGrammar."
    parser.parse(GrammarSpecTokenizer(spec))
    return grammar_class(parser.grammar.eval(parser.parses().next()), start)
