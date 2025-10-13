from .transpile import Param, ControlFlow, FunctionCall, Atom, BinOp, \
                        FunctionDecl, Assignment, Return, PrintCall, \
                        Entrypoint, EmptyLine
from parsy import forward_declaration, generate, whitespace, regex, string, \
                  seq, peek

expr = forward_declaration()
ws = whitespace.optional()
ws_scope = whitespace.at_least(0)
name = regex("[a-z][a-z0-9]*").desc("name")
param = seq(name.desc("parameter"), 
            (string(":") >> ws >> name.desc("type")).optional()) \
           .combine(Param)
params = param.sep_by(string(",") >> ws)


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
integer = regex("[0-9]+").map(lambda res: Atom(res, "int")) \
                         .desc("int")
decimal = regex("[0-9]+\.[0-9]+").map(lambda res: Atom(res, "float")) \
                                 .desc("float")
s = (string("\"") | string("'")) \
  + regex('[a-zA-Z0-9\ ]*') \
  + (string("\"") | string("'")).desc("string") # string and str are taken.

atom = (name | decimal | integer | s).desc("atom")


def make_bin_op(keyword):
    @generate
    def parser():
        lhs = yield ws >> (paren_expr | function_call | atom) << ws
        yield string(keyword)
        rhs = yield ws >> (expr | function_call | atom)
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
def function_decl():
    n = yield string("def") >> whitespace >> name
    p = yield string("(") >> params << string("):\n")
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
    return FunctionDecl(n, p, contents)


def lexer(code):
    if_stmt = ctrl_stmt("if")
    elif_stmt = ctrl_stmt("elif")
    while_stmt = ctrl_stmt("while")
    for_stmt = ctrl_stmt("for")

    control_flow = (if_stmt | elif_stmt | else_stmt |
                    while_stmt | for_stmt).desc("control flow")

    # Special binary op that requires a name on lhs.
    assignment = seq(
        name.desc("name"),
        (string(":") >> ws >> name).optional().desc("type"),
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
    binary_op = ((addition | \
                subtraction | \
                multiply | \
                assignment | \
                equality | \
                not_eq | \
                greater_than | \
                geq | \
                less_than | \
                leq)).desc("binary op")

    ret = seq(string("return") >> ws >> expr << string("\n").optional()) \
         .combine(Return)
    print_call = seq(string("print(") >> expr << string(")")) \
        .desc("print invocation") \
        .combine(PrintCall)

    # Handle this if statement as a special entrypoint for the program.
    entrypoint = seq(
            string("if __name__ == '__main__':\n    main()") |
            string('if __name__ == "__main__":\n    main()')
            ).desc("entrypoint").combine(Entrypoint)

    emptyline = seq(string("\n")).combine(EmptyLine)

    expr.become(entrypoint | \
                function_decl | \
                binary_op | \
                print_call |
                function_call | \
                control_flow | \
                ret |
                atom |
                emptyline)
    prog = expr.at_least(0)
    return prog.parse(code)
