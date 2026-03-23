def main():
    a: int = 0
    b: int = 1
    while a < 10:
        print(a)
        a, b = b, a+b


if __name__ == '__main__':
    main()
