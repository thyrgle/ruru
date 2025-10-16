from collections import defaultdict
from dataclasses import dataclass


class Expr:
    pass


@dataclass
class Name(Expr):
    name: str

    def __str__(self):
        return f'{self.name}'


class Program:
    """Keeps track of scope and which variables have been initialized.
    """
    scope: int = 0 # Number of spaces corresponds to scope / 4
    initialized: dict[int, set] = defaultdict(set) # Initialized vars in scope.
    entrypoint: bool = False # Did the user define a main function?
    premain: bool = True # Global stuff to run before main if needed. TODO
    use_unknown: bool = False
    use_rc: bool = False

    @staticmethod
    def scoped(f):
        def scoped_f(*args, **kwargs):
            return " " * 4 * Program.scope + f(*args, **kwargs)
        return scoped_f


@dataclass
class Class:
    name: Name
    body: list[Expr]

    @Program.scoped
    def __str__(self):
        struct = f"struct {self.name} {{\n"
        impl = f"impl {self.name} {{\n"
        Program.scope += 1
        for stmt in self.body:
            match stmt:
                case Assignment():
                    struct += str(stmt) + "\n"
                case FunctionDecl():
                    impl += str(stmt) + "\n"
                case _:
                    raise ValueError( # TODO Extend!
                            "Must be assignment or func decl in class"
                            )
        Program.scope -= 1
        struct += "}\n"
        impl += "}\n"
        return struct + impl


class List:
    def __init__(self, *items):
        self.items: list[Expr] = items

    @Program.scoped
    def __str__(self):
        cur_scope = Program.scope
        Program.scope = 0
        result = "vec![" + ",".join([str(item) for item in self.items]) + "]"
        Program.scope = cur_scope
        return result


class Dict:
    def __init__(self, *items):
        # Follows a key value pair.
        self.keys = []
        self.values = []
        # TODO

    @Program.scoped
    def __str__(self):
        result = "let " + self.name + " = HashMap::new();\n"
        for key, value in zip(self.key, self.value):
            result += self.name + ".insert(" + key + "," + value + ");\n"
        return result


class Set:
    def __init__(self, name, *elems):
        self.name = name
        self.elems = elems

    def __str__(self):
        result = "let " + self.name + ": HashSet<Unknown> = HashSet::new();\n"
        for elem in self.elems:
            result += self.name + ".insert(" + str(elem) + ");\n"
        return result


@dataclass
class Variable:
    name: Name
    lifetime: str | None
    type_: str

    @Program.scoped
    def __str__(self):
        if self.type_ is None:
            self.type_ = "Unknown"
        if self.lifetime is None:
            return self.name + ": " + "Rc<" + self.type + ">"
        # Lifetime is `.
        return self.name + ": " + self.type


@dataclass
class StringLiteral(Expr):
    contents: str
    
    def __str__(self):
        return f'"{self.contents}"'


@dataclass
class IntegerLiteral:
    contents: str

    def __str__(self):
        return self.contents


@dataclass
class PrintCall:
    exprs: list[Expr]

    @Program.scoped
    def __str__(self):
        cur_scope = Program.scope
        Program.scope = 0
        result = "println!("
        if len(self.exprs) == 0:
            return 'println!("")'
        elif len(self.exprs) == 1:
            match self.exprs[0]:
                case StringLiteral():
                    result += str(self.exprs[0]) 
                case IntegerLiteral():
                    result += '"{}", ' + str(self.exprs[0])
            result += ");"
        else:
            for expr in self.exprs:
                pass # TODO
        Program.scope = cur_scope
        return result


@dataclass
class Param:
    name: Name
    type_: str | None

    @Program.scoped
    def __str__(self):
        if self.type_ is None:
            return str(self.name) + ": Unknown"
        else:
            return str(self.name) + ": " + self.type_


@dataclass
class Entrypoint:
    code: str # Not really needed, but parsy always returns something.

    @Program.scoped
    def __str__(self):
        Program.entrypoint = True # A main function has been found.
        return ""


@dataclass
class FunctionDecl:
    name: Name
    params: list[Param]
    body: list[Expr]

    @Program.scoped
    def __str__(self):
        # Header
        result = "fn " + str(self.name) + "(" 
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
        result += "\n" + Program.scope * 4 * " " + "}"
        return result


@dataclass
class FunctionCall(Expr):
    name: Name
    args: list[str]

    @Program.scoped
    def __str__(self):
        if len(self.args) == 1:
            return str(self.name) + "(" + str(self.args[0]) + ")"
        else:
            return str(self.name) + "(" + \
                ", ".join([str(arg) for arg in self.args]) + \
            ")"


# Maps control statements to the equivalent control statement in Rust.
_ctrl_map: dict[str, str] = {
    "while": "while",
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
class For:
    iter_name: Name
    iterable: Expr
    body: list[Expr]
    
    @Program.scoped
    def __str__(self):
        result = str(self.iter_name) + "in " + str(self.iterable) + "{\n"
        Program.scope += 1
        result += "\n".join([str(stmt) for stmt in self.body])
        Program.scope -= 1
        return result


@dataclass
class With:
    stmt: Expr # Such and such
    name: Name # as name
    body: list[Expr]

    def __str__(self):
        return "" # TODO Convert to Rust somehow.



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
class Yield:
    expr: Expr

    @Program.scoped
    def __str__(self):
        result = "yield "
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
    var: Variable
    rhs: Expr

    @Program.scoped
    def __str__(self):
        # RHS should not have any indentation.
        cur_scope = Program.scope
        Program.scope = 0
        result = ""
        if self.var.name in Program.initialized[cur_scope]:
            result += str(self.var) + " = " + str(self.rhs) + ";"
        else:
            result += "let mut " + str(self.var.name) + ": Rc<Unknown> = " + \
                      "Rc::new(" + str(self.rhs) + ");"
            Program.initialized[cur_scope].add(self.var.name)
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


@dataclass
class Atom(Expr):
    value: str
    type_: str

    @Program.scoped
    def __str__(self):
        return self.value


def compute_preamble(result):
    preamble = ""
    if Program.use_unknown:
        preamble += "use ruru::Unknown;\n"
    if Program.use_rc:
        preamble += "use std::rc::Rc;\n"
    if preamble != "": # There were imports!
        preamble += "\n\n"
    return preamble + result


def main_template():
    return "\n\nfn main() {\n}"


def transpile(parse_tree):
    result = "\n".join([str(expr) for expr in parse_tree])
    # What stuff should be included?
    result = compute_preamble(result)
    # No main was found, make one!
    if not Program.entrypoint:
        result += main_template()
    return result
