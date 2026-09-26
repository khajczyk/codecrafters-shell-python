import sys
import os
import shutil
import subprocess

def main():
    while True:
        sys.stdout.write("$ ")
        user_input = input("")
        commands = ["exit", "echo", "type", "pwd", "cd"]
        output = ""
        redir_file = None

        if " > " in user_input:
            redir_split = user_input.split(" > ")
            redir_file = redir_split[1]
            user_input = redir_split[0]
        elif " 1> " in user_input:
            redir_split = user_input.split(" 1> ")
            redir_file = redir_split[1]
            user_input = redir_split[0]
        
        split = user_input.split(" ")
        if len(split) > 1:
            argument = " ".join(split[1:])
        

        if user_input == "exit":
            break
        elif split[0] == "echo":
            output = f"{" ".join(echo_quote_parser(argument))}\n"
        elif split[0] == "type":
            if argument in commands:
                output = f"{argument} is a shell builtin\n"
            else:
                if path := shutil.which(argument):
                    output = f"{argument} is {path}\n"
                else:
                    output = f"{argument}: not found\n"
        elif shutil.which(echo_quote_parser(user_input)[0]):
            if redir_file:
                file_dir = echo_quote_parser(redir_file)[0]
                os.makedirs("/".join(file_dir.split("/")[:-1]), exist_ok=True)
                with open(file_dir, "w") as file:
                    subprocess.call(echo_quote_parser(user_input), stdout=file)
            else:
                subprocess.call(echo_quote_parser(user_input))
        elif user_input == "pwd":
            output = os.path.abspath(os.getcwd()) + "\n"
        elif split[0] == "cd":
            try:
                if not argument or argument[0] == "~":
                    os.chdir(os.getenv("HOME"))
                else:
                    os.chdir(argument)
            except:
                output = f"cd: {argument}: No such file or directory\n"
        else:
            print(f"{user_input}: command not found")
        if output != "":
            if redir_file:
                file_dir = echo_quote_parser(redir_file)[0]
                os.makedirs("/".join(file_dir.split("/")[:-1]), exist_ok=True)
                with open(file_dir, "w") as file:
                    file.write(output)
            else:
                print(output, end="")
    pass

def echo_quote_parser(arg : str):
    opened = False
    parsed = ""
    hasContent = False
    result = []
    double_opened = False
    pass_one = False
    for char in arg:
        if pass_one:
            parsed += char
            pass_one = False
        elif char == "\\":
            hasContent = True
            if opened:
                parsed += char
            else:
                pass_one = True
        elif char == '"' and not opened:
            double_opened = not double_opened
            hasContent = True
        elif char == "'" and not double_opened:
            opened = not opened
            hasContent = True
        elif double_opened or (not double_opened and opened):
            parsed += char
        elif char == " ":
            if parsed or hasContent:
                result.append(parsed)
                hasContent = False
                parsed = ""
        else:
            parsed += char
            hasContent = True
    if parsed or hasContent:
        result.append(parsed)
    return result


if __name__ == "__main__":
    main()
