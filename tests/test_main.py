from src.ruru.lexer import lexer
from src.ruru.transpile import transpile


TEST_INPUTS = "tests/test_inputs/"
TEST_OUTPUTS = "tests/test_outputs/"

def test_hello_world():
    with open(TEST_INPUTS + "hello_world.py", "r") as fpy:
        with open(TEST_OUTPUTS + "hello_world.rs", "r") as fru:
            result = fru.read().rstrip("\n")
            # Don't worry about new lines just yet!
            assert transpile(lexer(fpy.read())).rstrip("\n") == result
