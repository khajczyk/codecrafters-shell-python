import contextlib
import sys
import os
import shutil
import subprocess
import readline
import enum
from dataclasses import dataclass
import io


BUILTINS = ["exit", "echo", "type", "pwd", "cd", "complete", "jobs", "history"]
DOUBLE_QUOTE_ESCAPES = {'$', '`', '"', '\\', '\n'}
REGISTERED_COMPLETES = {}
COMP_LINE = ""
COMP_POINT = ""
HISTORY: list[int, str] = []

class State(str, enum.Enum):
    RUNNING = "Running"
    DONE = "Done"

@dataclass(order=True)
class Job():
    id: int
    status: State
    command: str
    process : subprocess.Popen

JOBS: list[Job] = []

def print_jobs(stdout, only_done):
    last = len(JOBS) - 1
    for i, job in enumerate(JOBS):
        if job.process.poll() is not None:
            job.status = State.DONE
        if only_done and job.status != State.DONE:
            continue
        indicator = "+" if i == last else "-" if i == last - 1 else " "
        print(f"[{job.id}]{indicator} {job.status.value:<24}{job.command}", file=stdout)
    JOBS[:] = [j for j in JOBS if j.status != State.DONE]

def is_int(s: str) -> bool:
    try:
        int(s)
        return True
    except ValueError:
        return False

def run_builtin(command: str, args: list[str], stdout, stderr):
    if command == "echo":
        print(" ".join(args), file=stdout)
    elif command == "type":
        if not args:
            return
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
        target = os.path.expanduser(args[0]) if args else os.path.expanduser("~")
        try:
            os.chdir(target)
        except OSError:
            print(f"cd: {target}: No such file or directory", file=stderr)
    elif command == "complete":
        if not args:
            return
        if args[0] == "-C":
            REGISTERED_COMPLETES[args[2]] = args[1]
        elif args[0] == "-p":
            if args[1] in REGISTERED_COMPLETES:
                print(f"complete -C '{REGISTERED_COMPLETES[args[1]]}' {args[1]}", file=stdout)
            else:
                print(f"complete: {args[1]}: no completion specification", file=stderr)
        elif args[0] == "-r":
            REGISTERED_COMPLETES.pop(args[1], None)
    elif command == "jobs":
        print_jobs(stdout, only_done=False)
    elif command == "history":
        limit = 0
        if args and is_int(args[0]):
            limit = int(args[0])        
        for record in HISTORY[-limit:]:
            print(f"{record[0]} {record[1]}", file=stdout)


def run_pipeline(segments: list[str]):
    argvs = [parser(seg) for seg in segments]

    for argv in argvs:
        if argv[0] not in BUILTINS and not shutil.which(argv[0]):
            print(f"{argv[0]}: command not found", file=sys.stderr)
            return

    procs: list[subprocess.Popen] = []
    last_proc = None
    prev_out = None

    for i, argv in enumerate(argvs):
        is_last = i == len(argvs) -1
        command, *args = argv

        if command in BUILTINS:
            if prev_out:
                prev_out.close()
                prev_out = None
            if is_last:
                run_builtin(command, args, sys.stdout, sys.stderr)
            else:
                buf = io.StringIO()
                run_builtin(command, args, buf, sys.stderr)
                r, w = os.pipe()
                os.write(w, buf.getvalue().encode())
                os.close(w)
                prev_out = os.fdopen(r)
        else:
            proc = subprocess.Popen(
                argv, 
                stdin=prev_out, 
                stdout=None if is_last else subprocess.PIPE)
            if prev_out:
                prev_out.close()
            prev_out = proc.stdout
            procs.append(proc)
            if is_last:
                last_proc = proc

    if last_proc:
        last_proc.wait()

    for proc in procs:
        if proc.poll() is None:
            proc.terminate()
        proc.wait()


def main():
    readline.set_completer(complete)
    readline.set_completer_delims(" \t")
    readline.parse_and_bind("tab: complete")
    while True:
        user_input = input("$ ")
        length = 1 if len(HISTORY) == 0 else len(HISTORY) + 1
        HISTORY.append(length, user_input)
        segments = pipe_split(user_input)

        if len(segments) > 1:
            run_pipeline(segments)
            print_jobs(sys.stdout, True)
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
            elif command in BUILTINS:
                run_builtin(command, args, stdout, stderr)
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

        print_jobs(sys.stdout, True)
            
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
