from collections import defaultdict
from dataclasses import dataclass
from parsy import forward_declaration, generate, whitespace, regex, string, \
                  seq, peek
from pprint import pprint


class Program:
    """Keeps track of scope and which variables have been initialized.
    """
    scope: int = 0 # Number of spaces corresponds to scope / 4
    initialized: dict[int, set] = defaultdict(set) # Initialized vars in scope.
    entrypoint = False # Did the user define a main function?
    premain = True # Global stuff to run before main if needed. TODO
    use_any = True
    use_unknown = False
    use_rc = True

    @staticmethod
    def scoped(f):
        def scoped_f(*args, **kwargs):
            return " " * 4 * Program.scope + f(*args, **kwargs)
        return scoped_f


class Expr:
    pass


@dataclass
class PrintCall:
    expr: Expr
    
    @Program.scoped
    def __str__(self):
        cur_scope = Program.scope
        Program.scope = 0
        result = "println!("
        result += str(self.expr) 
        result += ");"
        Program.scope = cur_scope
        return result


@dataclass
class Variable:
    name: str
    type_: str | None

    @Program.scoped
    def __str__(self):
        if self.type_ is None:
            return self.name + ": Unknown"
        else:
            return self.name + ": " + self.type_

@dataclass
class Entrypoint:
    code: str # Not really needed, but parsy always returns something.

    @Program.scoped
    def __str__(self):
        Program.entrypoint = True # A main function has been found.
        return ""


@dataclass
class FunctionDecl:
    name: str
    params: list[Variable]
    body: list[Expr]

    @Program.scoped
    def __str__(self):
        # Header
        result = "fn " + self.name + "(" 
        if self.params is not None: # Check if there are no parameters.
            result += \
            ", ".join([str(param) for param in self.params]) + \
            ") {\n"
        else:
            result += ") {\n"
        # Body
        Program.scope += 1
        result += "\n".join([str(stmt) for stmt in self.body])
        Program.scope -= 1
        # End
        result += "\n}"
        return result


@dataclass
class FunctionCall(Expr):
    name: str
    args: list[str]

    @Program.scoped
    def __str__(self):
        if len(self.args) == 1:
            return self.name + "(" + str(self.args[0]) + ")"
        else:
            return self.name + "(" + \
                ", ".join([str(arg) for arg in self.args]) + \
            ")"


# Maps control statements to the equivalent control statement in Rust.
_ctrl_map: dict[str, str] = {
    "while": "while",
    "for": "for",
    "if": "if",
    "elif": "else if",
    "else": "else"
}


@dataclass
class ControlFlow:
    stmt: str
    cond: Expr
    body: [Expr]

    @Program.scoped
    def __str__(self):
        cur_scope = Program.scope
        result = _ctrl_map[self.stmt] + " "
        Program.scope = 0
        if self.cond: # Handles the case of "else"
            result += str(self.cond)
        Program.scope = cur_scope
        result += " {\n"
        Program.scope += 1
        result += ";".join([str(stmt) for stmt in self.body])
        Program.scope = cur_scope
        result += "\n" + "    " * cur_scope + "}"
        return result


@dataclass
class Return:
    expr: Expr

    @Program.scoped
    def __str__(self):
        result = "return "
        cur_scope = Program.scope
        Program.scope = 0
        result += str(self.expr) + ";"
        Program.scope = cur_scope
        return result


@dataclass
class EmptyLine(Expr):
    noop: str
    """Essentially a no-op when a blank line is encountered."""
    @Program.scoped
    def __str__(self):
        return ""


@dataclass
class Assignment:
    name: str
    type_: str
    rhs: Expr

    @Program.scoped
    def __str__(self):
        # RHS should not have any indentation.
        cur_scope = Program.scope
        Program.scope = 0
        result = ""
        if self.name in Program.initialized[cur_scope]:
            result += self.name + " = " + str(self.rhs) + ";"
        else:
            result += "let mut " + self.name + ": Rc<Unknown> = " + \
                      "Rc::new(" + str(self.rhs) + ");"
            Program.initialized[cur_scope].add(self.name)
        # Resume as usual.
        Program.scope = cur_scope
        return result



@dataclass
class BinOp(Expr):
    lhs: Expr
    op: str
    rhs: Expr

    @Program.scoped
    def __str__(self):
        # RHS should not have any indentation.
        cur_scope = Program.scope
        Program.scope = 0
        result = str(self.lhs) + " " + self.op + " " + str(self.rhs)
        # Resume original scope.
        Program.scope = cur_scope
        return result


expr = forward_declaration()
ws = whitespace.optional()
ws_scope = whitespace.at_least(0)
name = regex("[a-z][a-z0-9]*").desc("name")
param = seq(name.desc("parameter"), 
            (string(":") >> ws >> name.desc("type")).optional()) \
           .combine(Variable)
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
integer = regex("[0-9]+").desc("int")
decimal = regex("[0-9]+\.[0-9]+").desc("float")
s = (string("\"") | string("'")) \
  + regex('[a-zA-Z0-9\ ]*') \
  + (string("\"") | string("'")).desc("string") # string and str are taken.

atom = (name | decimal | integer | s).desc("atom")


def make_bin_op(keyword):
    @generate
    def parser():
        lhs = yield ws >> (paren_expr | function_call | atom) << ws
        yield string(keyword)
        rhs = yield ws >> (expr | function_call | atom) << ws
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


def compute_preamble(result):
    preamble = ""
    if Program.use_any:
        preamble += "use std::any::Any;\n"
    if Program.use_rc:
        preamble += "use std::rc::Rc;\n"
    if preamble != "": # There were imports!
        preamble += "\n\n"
    return preamble + result


def main_template():
    return "\n\nfn main() {\n}"


def compile(parse_tree):
    result = "\n".join([str(expr) for expr in parse_tree])
    # What stuff should be included?
    result = compute_preamble(result)
    # No main was found, make one!
    if not Program.entrypoint:
        result += main_template()
    return result


def main():
    with open("test_inputs/assignments.py", "r") as fpy:
        lex = lexer(fpy.read())
        pprint(lex)
        #print(compile(lex))


if __name__ == "__main__":
    main()
