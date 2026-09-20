import sys


def main():
    # TODO: Uncomment the code below to pass the first stage
    sys.stdout.write("$ ")
    user_input = input("")
    sys.stdout.write(f"{user_input}: command not found")
    pass


if __name__ == "__main__":
    main()
