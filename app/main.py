import contextlib
import sys
import os
import shutil
import subprocess
import readline
import enum
from dataclasses import dataclass


BUILTINS = ["exit", "echo", "type", "pwd", "cd", "complete", "jobs"]
DOUBLE_QUOTE_ESCAPES = {'$', '`', '"', '\\', '\n'}
REGISTERED_COMPLETES = {}
JOBS: list[Job] = []
COMP_LINE = ""
COMP_POINT = ""

class State(str, enum.Enum):
    RUNNING = "Running"
    DONE = "Done"

@dataclass(order=True)
class Job():
    id: int
    status: State
    command: str
    process : subprocess.Popen

def main():
    readline.set_completer(complete)
    readline.set_completer_delims(" \t")
    readline.parse_and_bind("tab: complete")
    while True:
        user_input = input("$ ")
        command_split = pipe_split(user_input)

        if len(command_split) > 1:
            processes = []
            first_command, last_command = command_split[0], command_split[-1]
            

            if shutil.which(first_command):
                tokens = parser(first_command)
                p1 = subprocess.Popen(tokens, stdout=subprocess.PIPE)
                processes.append(p1.stdout)

            if len(command_split) > 2:
                middle_commands = command_split[1:-1]
                for mid_command in middle_commands:
                    if shutil.which(mid_command):
                        tokens = parser(mid_command)
                        p = subprocess.Popen(tokens, stdin=processes[-1], stdout=subprocess.PIPE)
                        processes.append(p.stdout)

            if shutil.which(last_command):
                tokens = parser(last_command)
                p = subprocess.Popen(tokens, stdin=processes[-1], stdout=None)
                processes.append(p.stdout)
                p.wait()
    
            continue


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
                elif args[0] == "-p":
                    if args[1] in REGISTERED_COMPLETES:
                        print(f"complete -C '{REGISTERED_COMPLETES[args[1]]}' {args[1]}")
                    else:
                        print(f"complete: {args[1]}: no completion specification", file=stderr)
                elif args[0] == "-r":
                    del REGISTERED_COMPLETES[args[1]]
            elif command == "jobs":
                for job in JOBS:
                    indicator =  "+" if job == JOBS[-1] else "-" if job == JOBS[-2] else " "
                    if job.process.poll() is not None:
                        job.status = State.DONE
                    print(f"[{job.id}]{indicator} {job.status.value}{" " * (24 - len(job.status.value))}{job.command}")
                JOBS[:] = [j for j in JOBS if j.status != State.DONE]
            elif shutil.which(command):
                if tokens[-1] == "&":
                    tokens = tokens[:-1]
                    process = subprocess.Popen(tokens, stdout=stdout, stderr=stderr, start_new_session=True)
                    job_id = 1 if len(JOBS) == 0 else JOBS[-1].id + 1
                    job = Job(id=job_id, status=State.RUNNING, command=" ".join(tokens), process=process)
                    JOBS.append(job)
                    print(f"[{job.id}] {process.pid}")
                else:
                    subprocess.call(tokens, stdout=stdout, stderr=stderr)
            else:
                print(f"{command}: command not found", file=stderr)

            for job in JOBS:
                indicator =  "+" if job == JOBS[-1] else "-" if job == JOBS[-2] else " "
                if job.process.poll() is not None:
                    job.status = State.DONE
                    print(f"[{job.id}]{indicator} {job.status.value}{" " * (24 - len(job.status.value))}{job.command}")
                    JOBS.remove(job)    

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

def pipe_split(input: str): 
    return input.split(" | ") if " | " in input else [input]

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
        line = readline.get_line_buffer()
        args = line.split(" ")
        arg1 = args[0]
        if arg1 in REGISTERED_COMPLETES:
            arg2 = args[-1]
            arg3 = args[-2] if len(args) > 1 else ""
            result = subprocess.run(
                [REGISTERED_COMPLETES[arg1], arg1, arg2, arg3],
                capture_output=True, 
                text=True, 
                cwd=os.getcwd(),
                env={**os.environ, "COMP_LINE": line, "COMP_POINT": str(len(line))}
            )
            if result.stdout:
                matches.extend(result.stdout.splitlines())
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
