import sys
import os

def main():
    while True:
        sys.stdout.write("$ ")
        user_input = input("")
        commands = ["exit", "echo", "type"]
        if " " in user_input:
            argument = user_input.split(" ", 1)[1]
        if user_input == "exit":
            break
        elif user_input.startswith("echo"):
            sys.stdout.write(f"{argument}\n")
        elif user_input.startswith("type"):
            if argument in commands:
                sys.stdout.write(f"{argument} is a shell builtin\n")
            else:
                base_path = os.path.split(argument)
                if os.path.isdir(base_path[0]) and os.access(argument, os.X_OK):
                    sys.stdout.write(f"{base_path[1]} is {argument}")
                else:
                    sys.stdout.write(f"{argument}: not found\n")
        else:
            sys.stdout.write(f"{user_input}: command not found\n")
    pass


if __name__ == "__main__":
    main()
