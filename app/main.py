import sys
import os
import shutil
import subprocess

def main():
    while True:
        sys.stdout.write("$ ")
        user_input = input("")
        commands = ["exit", "echo", "type", "pwd", "cd"]
        split = user_input.split(" ")
        if len(split) > 1:
            argument = " ".join(split[1:])

        
        if user_input == "exit":
            break
        elif user_input.startswith("echo"):
            print(f"{echo_quote_parser(argument)}")
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
        elif user_input.startswith("cd "):
            try:
                if not argument or argument[0] == "~":
                    os.chdir(os.getenv("HOME"))
                else:
                    os.chdir(argument)
            except:
                print(f"cd: {argument}: No such file or directory")
        else:
            sys.stdout.write(f"{user_input}: command not found\n")
    pass

def echo_quote_parser(arg : str):
    closing = True
    parsed = ""
    for char in arg:
        if char == "'":
            closing = not closing
        elif closing == True and len(parsed) > 1 and char == " " and parsed[-1] == " ":
            pass
        else:
            parsed += char
    return parsed


if __name__ == "__main__":
    main()
