import sys
import os
import shutil
import subprocess

def main():
    while True:
        sys.stdout.write("$ ")
        user_input = input("")
        commands = ["exit", "echo", "type", "pwd"]
        split = user_input.split(" ")
        if len(split) > 1:
            argument = " ".join(split[1:])
        if user_input == "exit":
            break
        elif user_input.startswith("echo"):
            sys.stdout.write(f"{argument}\n")
        elif user_input.startswith("type"):
            if argument in commands:
                sys.stdout.write(f"{argument} is a shell builtin\n")
            else:
                if path := shutil.which(argument):
                    sys.stdout.write(f"{argument} is {path}\n")
                else:
                    sys.stdout.write(f"{argument}: not found\n")
        elif shutil.which(split[0]):
            subprocess.call(split)
        elif user_input == "pwd":
            print(os.path.abspath(os.getcwd()))
        else:
            sys.stdout.write(f"{user_input}: command not found\n")
    pass


if __name__ == "__main__":
    main()
