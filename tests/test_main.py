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
OUTPUT_FILES = sorted(os.listdir(TEST_OUTPUTS))


def run(ruru_code):
    rust_code = transpile(lexer(ruru_code))
    with open('temp.rs', mode="w") as rust_file:
        rust_file.write(rust_code)
    subprocess.run(["rustc", 'temp.rs', "-o", "temp_binary"])
    output = subprocess.run(["./temp_binary"], capture_output=True)
    pathlib.Path("temp_binary").unlink()
    pathlib.Path("../temp.rs").unlink()
    return output


@pytest.mark.parametrize("in_, out", zip(INPUT_FILES, OUTPUT_FILES))
def test_outputs(in_, out):
    assert run(in_) == run(out)


def test_rust_outputs():
    with open(TEST_INPUTS + "hello_world.py", "r") as fpy:
        with open(TEST_OUTPUTS + "hello_world.rs", "r") as fru:
            result = fru.read().rstrip("\n")
            # Don't worry about new lines just yet!
            assert transpile(lexer(fpy.read())).rstrip("\n") == result
