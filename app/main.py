import contextlib
import sys
import os
import shutil
import subprocess
import readline

BUILTINS = ["exit", "echo", "type", "pwd", "cd", "complete"]
DOUBLE_QUOTE_ESCAPES = {'$', '`', '"', '\\', '\n'}
REGISTERED_COMPLETES = {}

def main():
    readline.set_completer(complete)
    readline.set_completer_delims(" \t")
    readline.parse_and_bind("tab: complete")
    while True:
        user_input = input("$ ")
        command_text, redirect_target, stream, append = redirect(user_input)
        tokens = parser(command_text)

        if not tokens:
            continue
        
        command, *args = tokens

        if redirect_target is not None:
            filename = parser(redirect_target)[0]
            directory = os.path.dirname(filename)
            if directory:
                os.makedirs(directory, exist_ok=True)
            append_to_file = "a" if append else "w"
            destination = open(filename, append_to_file)
        else:
            destination = contextlib.nullcontext(sys.stdout)
        
        with destination as file:
            stdout = file if stream == "stdout" else sys.stdout
            stderr = file if stream == "stderr" else sys.stderr

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
                    print(f"{target}: not found", file=stderr)

            elif command == "pwd":
                print(os.getcwd(), file=stdout)

            elif command == "cd":
                try:
                    target = os.path.expanduser(args[0]) if args else os.path.expanduser("~")
                    os.chdir(target)
                except:
                    print(f"cd: {target}: No such file or directory", file=stderr)
            elif command == "complete":
                if args[0] == "-C":
                    REGISTERED_COMPLETES[args[2]] = args[1]
                if args[0] == "-p":
                    if args[1] in REGISTERED_COMPLETES:
                        print(f"complete -C '{REGISTERED_COMPLETES[args[1]]}' {args[1]}")
                    else:
                        print(f"complete: {args[1]}: no completion specification", file=stderr)

            elif shutil.which(command):
                subprocess.call(tokens, stdout=stdout, stderr=stderr)
            else:
                print(f"{command}: command not found", file=stderr)
    
def redirect(input : str):
    for operator, stream, append in [
        (" > ", "stdout", False),
        (" >> ", "stdout", True),
        (" 1> ", "stdout", False),
        (" 1>> ", "stdout", True),
        (" 2> ", "stderr", False),
        (" 2>> ", "stderr", True),
        ]:
        command, separator, filename = input.partition(operator)
        if separator:
            return command, filename, stream, append
    return input, None, None, False

def parser(arg : str):
    current_arg = ""
    argument_started = False
    escape = False
    result = []
    quote = None
    for char in arg:
        if escape:
            if quote == '"' and char not in DOUBLE_QUOTE_ESCAPES:
                current_arg += "\\"
            current_arg += char
            escape = False
        elif char == "\\":
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

def complete(text, state):
    matches = []
    before_word = readline.get_line_buffer()[:readline.get_begidx()]

    if not before_word.strip():
        matches = sorted(
            command for command in BUILTINS
            if command.startswith(text)
        )
        
        for path_directory in os.get_exec_path():
            path_directory = path_directory or "."
            if os.path.isdir(path_directory):
                matches.extend(
                    name for name in os.listdir(path_directory)
                    if name.startswith(text)
                )
    else:
        print(before_word)
        if before_word.strip() in REGISTERED_COMPLETES:
            result = subprocess.run(
                REGISTERED_COMPLETES[before_word.strip()], capture_output=True, text=True, cwd=os.getcwd()
            )
            print("text")
            if result.stdout.strip("\n"):
                print(result.stdout.strip("\n"), end=" ")
            else:
                print("\x07")
        else:
            matches.extend(
                name for name in os.listdir()
                if name.startswith(text)
            )

            if "/" in text:
                dir, prefix = os.path.split(text)
                if os.path.isdir(dir):
                    matches.extend(
                        os.path.join(dir, name)
                        for name in os.listdir(dir)
                        if name.startswith(prefix)
                    )

    matches = sorted(set(matches))

    if state < len(matches):
        match = matches[state]
        return match + ("/" if os.path.isdir(match) else " ")

    return None

if __name__ == "__main__":
    main()
