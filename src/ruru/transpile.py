from collections import defaultdict
from dataclasses import dataclass


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
class Class:
    name: str
    body: list[Expr]

    @Program.scoped
    def __str__(self):
        pass # TODO Need two parts in Rust I think!


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
class Param:
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
    params: list[Param]
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


@dataclass
class Atom(Expr):
    value: str
    type_: str

    @Program.scoped
    def __str__(self):
        return self.value


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


def transpile(parse_tree):
    result = "\n".join([str(expr) for expr in parse_tree])
    # What stuff should be included?
    result = compute_preamble(result)
    # No main was found, make one!
    if not Program.entrypoint:
        result += main_template()
    return result
