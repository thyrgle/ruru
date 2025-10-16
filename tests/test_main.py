from io import StringIO
from contextlib import redirect_stdout
import os
import pytest
import subprocess
import pathlib
from src.ruru.lexer import lexer
from src.ruru.transpile import transpile


TEST_INPUTS = "tests/test_inputs/"
TEST_OUTPUTS = "tests/test_outputs/"
# Each input file has a corresponding output file.
INPUT_FILES = sorted(os.listdir(TEST_INPUTS))


def run(ruru_code):
    rust_code = transpile(lexer(ruru_code))
    with open('temp.rs', mode="w") as rust_file:
        rust_file.write(rust_code)
    subprocess.run(["rustc", 'temp.rs', 
                    "-o", "temp_binary"])
    output = subprocess.run(["./temp_binary"], capture_output=True).stdout
    pathlib.Path("temp_binary").unlink()
    pathlib.Path("temp.rs").unlink()
    return output


@pytest.mark.parametrize("file_name", INPUT_FILES)
def test_outputs(file_name):
    with open(TEST_INPUTS + file_name) as file:
        exec_output = StringIO()
        with redirect_stdout(exec_output):
            exec(file.read())
        assert run(file.read()) == exec_output.getvalue().encode("utf-8")


def test_rust_outputs():
    with open(TEST_INPUTS + "hello_world.py", "r") as fpy:
        with open(TEST_OUTPUTS + "hello_world.rs", "r") as fru:
            result = fru.read().rstrip("\n")
            # Don't worry about new lines just yet!
            assert transpile(lexer(fpy.read())).rstrip("\n") == result
