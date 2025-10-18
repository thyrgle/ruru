from .transpile import Param, ControlFlow, FunctionCall, Atom, BinOp, \
                        FunctionDecl, Assignment, Return, PrintCall, \
                        Entrypoint, EmptyLine, Class, Variable, List, Dict, \
                        Yield, With, For, IntegerLiteral, StringLiteral, \
                        Name, RangeCall, Comment, TupleUnpack
from parsy import forward_declaration, generate, whitespace, regex, string, \
                  seq, peek


expr = forward_declaration()
ws = whitespace.optional()
ws_scope = whitespace.at_least(0)
name = regex(r"\w+") \
      .desc("name") \
      .map(Name)
var = seq(name,
          string("`").optional(),
          (string(":") >> ws >> name.desc("type")).optional()) \
          .combine(Variable)
param = seq(name.desc("parameter"), 
            (string(":") >> ws >> name.desc("type")).optional()) \
           .combine(Param)
params = param.sep_by(string(",") << ws)


def with_stmt():
    yield string("with")
    stmt = yield ws >> expr << ws << string("as")
    with_name = yield ws >> name << string(":\n")
    scope = yield peek(ws_scope.concat().map(len))
    next_indent = scope
    contents = []
    while True:
        next_indent = yield peek(ws_scope.concat().map(len))
        if next_indent == scope:
            body = yield string(" " * scope) >> expr
            contents.append(body)
        else:
            break
    return With(stmt, with_name, contents)


def ctrl_stmt(keyword):
    @generate
    def parser():
        yield string(keyword)
        cond = yield ws >> expr.desc("condition") << ws << string(":\n")
        scope = yield peek(ws_scope.concat().map(len))
        next_indent = scope
        contents = []
        while True:
            next_indent = yield peek(ws_scope.concat().map(len))
            if next_indent == scope:
                body = yield string(" " * scope) >> expr
                contents.append(body)
            else:
                break
        return ControlFlow(keyword, cond, contents)
    return parser


paren_expr = string("(") >> expr << string(")")
function_call = seq(
    name, 
    string("(") >> expr.at_least(0) << string(")")
).combine(FunctionCall)
integer = regex("[0-9]+").map(IntegerLiteral) \
                         .desc("int")
decimal = regex(r"[0-9]*+\.[0-9]+").map(lambda res: Atom(res, "float")) \
                                 .desc("float")
string_ = (string('"') >> regex(r'[^"\\]+') << string('"')).map(StringLiteral)

atom = (string_ | decimal | integer | name).desc("atom")


def make_bin_op(keyword):
    @generate
    def parser():
        lhs = yield ws >> (function_call | paren_expr | atom) << ws
        yield string(keyword)
        rhs = yield ws >> (function_call | atom | expr) << ws
        return BinOp(lhs, keyword, rhs)
    return parser


@generate
def else_stmt():
    """ Else is *similar* to the other control flow, but does not have a
    condition to check. So it is separated out here.
    """
    yield string("else:\n")
    scope = yield peek(ws_scope.concat().map(len))
    next_indent = scope
    contents = []
    while True:
        next_indent = yield peek(ws_scope.concat().map(len))
        if next_indent == scope:
            body = yield string(" " * scope) >> expr
            contents.append(body)
        else:
            break
    return ControlFlow("else", None, contents)


@generate
def for_stmt():
    """ For is *similar* to the other control flow, but it is stricter in form.
    for name in iterable:
    """
    # TODO
    iter_name = yield string("for") >> ws >> name << ws << string("in") << ws
    iterable = yield expr << ws << string(":\n")
    scope = yield peek(ws_scope.concat().map(len))
    next_indent = scope
    contents = []
    while True:
        next_indent = yield peek(ws_scope.concat().map(len))
        if next_indent == scope:
            body = yield string(" " * scope) >> expr
            contents.append(body)
        else:
            break
    return For(iter_name, iterable, contents)


@generate
def function_decl():
    n = yield string("def") >> whitespace >> ws >> name
    p = yield string("(") >> params << string(")")
    return_type = yield (string(":\n").map(lambda res: None) | 
                         string(" -> ") >> ws >> name << string(":\n"))
    scope = yield peek(ws_scope.concat().map(len))
    next_indent = scope
    contents = []
    while True:
        next_indent = yield peek(ws_scope.concat().map(len))
        if next_indent >= scope:
            body = yield string(" " * scope) >> expr
            contents.append(body)
        else:
            break
    return FunctionDecl(n, p, return_type, contents)


@generate
def class_decl():
    n = yield string("class") >> whitespace >> name << string(":\n")
    scope = yield peek(ws_scope.concat().map(len))
    next_indent = scope
    contents = []
    while True:
        next_indent = yield peek(ws_scope.concat().map(len))
        if next_indent >= scope:
            body = yield string(" " * scope) >> expr
            contents.append(body)
        else:
            break
    return Class(n, contents)


if_stmt = ctrl_stmt("if")
elif_stmt = ctrl_stmt("elif")
while_stmt = ctrl_stmt("while")

control_flow = (if_stmt | elif_stmt | else_stmt |
                while_stmt | for_stmt).desc("control flow")

comment = (string("#") >> regex(r".*") << string("\n")).map(Comment)

# Tuple unpack.
tuple_unpack = seq(
    (ws >> name << ws).sep_by(string(", ")) << string("="),
    (ws >> expr << ws).sep_by(string(","))
).combine(TupleUnpack)

# Special binary op that requires a name on lhs.
assignment = seq(
    var,
    ws >> string("=") >> ws >> expr << string("\n").optional()
).combine(Assignment)

addition = make_bin_op("+")
subtraction = make_bin_op("-")
multiply = make_bin_op("*")
equality = make_bin_op("==")
not_eq = make_bin_op("!=")
greater_than = make_bin_op(">")
geq = make_bin_op(">=")
less_than = make_bin_op("<")
leq = make_bin_op("<=")
binary_op = (tuple_unpack | \
             addition | \
             subtraction | \
             multiply | \
             assignment | \
             equality | \
             not_eq | \
             greater_than | \
             geq | \
             less_than | \
             leq).desc("binary op")

return_ = seq(string("return") >> ws >> expr << string("\n").optional()) \
         .combine(Return)
yield_ = seq(string("return") >> ws >> expr << string("\n").optional()) \
        .combine(Yield)
print_call = (string("print(") >> expr.sep_by(string(",")) << string(")")) \
    .desc("print call").map(PrintCall)
range_call = (string("range(") >> expr << string(")")) \
    .desc("range call").map(RangeCall)


# Handle this if statement as a special entrypoint for the program.
entrypoint = seq(
        string("if __name__ == '__main__':\n    main()") |
        string('if __name__ == "__main__":\n    main()')
        ).desc("entrypoint").combine(Entrypoint)

emptyline = seq(string("\n")).combine(EmptyLine)

list_ = ((ws >> string("[") << ws) >> \
         (ws >> expr << ws).sep_by(string(",")) << \
         (ws >> string("]"))).combine(List)
#TODO: Handle semicolon!
dict_ = ((ws >> string("{") << ws) >> \
          seq(ws >> expr << ws, # Key
              string(":") >> ws >> expr << ws) # Value
         .sep_by(string(",")) << (ws >> string("}"))).combine(Dict)
set_ = ((ws >> string("{") << ws) >> \
        (ws >> expr << ws).sep_by(string(",")) << \
        (ws >> string("}"))).combine(Dict)

expr.become(entrypoint |
            comment |
            binary_op |
            print_call |
            range_call |
            function_call |
            function_decl |
            class_decl |
            control_flow |
            return_ |
            yield_ |
            atom |
            list_ |
            dict_ |
            set_ |
            emptyline)
prog = expr.at_least(0)


def lexer(code):
    return prog.parse(code)


def partial_lexer(code):
    return prog.parse_partial(code)
