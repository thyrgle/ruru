from .main import compile, lexer


def test_hello_world():
    with open("test_inputs/hello_world.py", "r") as fpy:
        with open("test_outputs/hello_world.rs", "r") as fru:
            result = fru.read().rstrip("\n")
            # Don't worry about new lines just yet!
            assert compile(lexer(fpy.read())).rstrip("\n") == result
