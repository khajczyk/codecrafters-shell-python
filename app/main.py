import contextlib
import sys
import os
import shutil
import subprocess

BUILTINS = ["exit", "echo", "type", "pwd", "cd"]
DOUBLE_QUOTE_ESCAPES = {'$', '`', '"', '\\', '\n'}

def main():
    while True:
        user_input = input("$ ")
        command_text, redirect_target = redirect(user_input)
        tokens = parser(command_text)

        if not tokens:
            continue
        
        command, *args = tokens

        if redirect_target is not None:
            filename = parser(redirect_target)[0]
            destination = open(filename, "w")
        else:
            destination = contextlib.nullcontext(sys.stdout)
        
        with destination as stdout:
            if command == "exit":
                break
            elif command == "echo":
                print(" ".join(args), file=stdout)
            elif command == "type":
                target = args[0]

                if target in BUILTINS:
                    print(f"{target} is a shell builtin", file=stdout)
                elif path := shutil.which(target):
                    print(f"{target} is {path}", file=stdout)
                else:
                    print(f"{target}: not found", file=stdout)

            elif command == "pwd":
                print(os.getcwd(), file=stdout)

            elif command == "cd":
                try:
                    target = os.path.expanduser(args[0]) if args else os.path.expanduser("~")
                    os.chdir(target)
                except:
                    print(f"cd: {target}: No such file or directory", file=stdout)

            elif shutil.which(command):
                subprocess.call(tokens, stdout=stdout)
            else:
                print(f"{command}: command not found", file=stdout)
    pass

def redirect(input : str):
    for operator in [" > ", " 1> ", " 2> "]:
        command, separator, filename = input.partition(operator)
        if separator:
            return command, filename
    return input, None

def parser(arg : str):
    current_arg = ""
    argument_started = False
    escape = False
    result = []
    quote = None
    for char in arg:
        if escape:
            current_arg += char
            escape = False
        elif char in DOUBLE_QUOTE_ESCAPES:
            argument_started = True
            if quote == "'":
                current_arg += char
            else:
                escape = True
        elif char == '"' and quote != "'":
            quote = '"' if quote is None else None
            argument_started = True
        elif char == "'" and quote != '"':
            quote = "'" if quote is None else None
            argument_started = True
        elif quote is not None:
            current_arg += char
        elif char == " ":
            if current_arg or argument_started:
                result.append(current_arg)
                argument_started = False
                current_arg = ""
        else:
            current_arg += char
            argument_started = True
    if current_arg or argument_started:
        result.append(current_arg)
    return result


if __name__ == "__main__":
    main()
