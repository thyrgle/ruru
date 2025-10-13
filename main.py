import argparse
from src.lexer import lexer
from src.transpile import transpile 


def main():
    # Not related to the actual lexer, just for the command line.
    parser = argparse.ArgumentParser(prog="ruru")
    parser.add_argument("file", help="Input file to transpile")
    args = parser.parse_args()
    with open(args.file, "r") as fpy:
        lex = lexer(fpy.read())
        print(transpile(lex))


if __name__ == "__main__":
    main()
