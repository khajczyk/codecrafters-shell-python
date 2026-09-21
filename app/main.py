import sys


def main():
    while True:
        sys.stdout.write("$ ")
        user_input = input("")
        if user_input == "exit":
            break
        elif user_input.startswith("echo"):
            sys.stdout.write(user_input.split("echo ")[1] + "\n")
        else:
            sys.stdout.write(f"{user_input}: command not found\n")
    pass


if __name__ == "__main__":
    main()
