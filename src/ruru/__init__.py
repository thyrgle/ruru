import argparse
import subprocess
import pathlib
from .lexer import lexer, partial_lexer
from .transpile import transpile 


def run(rust_code):
    with open('temp.rs', mode="w") as rust_file:
        rust_file.write(rust_code)
    subprocess.run(["rustc", 'temp.rs', "-o", "temp_binary"])
    subprocess.run(["./temp_binary"])
    pathlib.Path("temp_binary").unlink()
    pathlib.Path("temp.rs").unlink()


def main():
    # Not related to the actual lexer, just for the command line.
    parser = argparse.ArgumentParser(prog="ruru")
    parser.add_argument("file", help="Input file to transpile")
    parser.add_argument("--lexer", help="Lexer output.", action="store_true")
    parser.add_argument("--lexer-partial", 
                        help="Lexer using parse_partial",
                        action="store_true")
    parser.add_argument("--rust", help="Rust output.", action="store_true")
    args = parser.parse_args()
    with open(args.file, "r") as fpy:
        if args.lexer_partial:
            print(partial_lexer(fpy.read()))
            return
        lex = lexer(fpy.read())
        if args.lexer:
            print(lex)
            return
        rust_code = transpile(lex)
        if args.rust:
            print(rust_code)
            return
        run(rust_code)
