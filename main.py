from src.lexer import lexer
from src.transpile import transpile

def main():
    with open("test_inputs/assignments.py", "r") as fpy:
        lex = lexer(fpy.read())
        #pprint(lex)
        print(transpile(lex))


if __name__ == "__main__":
    main()
