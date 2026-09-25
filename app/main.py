import sys
import shutil
import subprocess

def main():
    while True:
        sys.stdout.write("$ ")
        user_input = input("")
        commands = ["exit", "echo", "type"]
        if " " in user_input:
            split = user_input.split(" ")
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
        elif command := shutil.which(user_input.split(" ")[0]):
            subprocess.call(split)
        else:
            sys.stdout.write(f"{user_input}: command not found\n")
    pass


if __name__ == "__main__":
    main()
