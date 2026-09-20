import sys


def main():
    while True:
        sys.stdout.write("$ ")
        user_input = input("")
        sys.stdout.write(f"{user_input}: command not found\n")
    pass


if __name__ == "__main__":
    main()
