from io import StringIO
from typing import Iterable, Dict

class Dockerfile:
    def __init__(self, image: str):
        self.__writer = StringIO(newline="")
        self.__write_line(f"FROM {image}")

    def __write_line(self, line: str):
        self.__writer.writelines([f"{line}\n"])

    def __str__(self):
        self.__writer.flush()

        return self.__writer.getvalue()
    
    def arg(self, **kwargs: Dict[str, str]):
        for key, value in kwargs.items():
            self.__write_line(f"ARG {key}={value}")
    
    def cmd(self, *cmd_args: Iterable[str]):
        cmd_string = ", ".join(f'"{c}"' for c in cmd_args)
        self.__write_line(f"CMD [{cmd_string}]")

    def copy(self, source: str, destinsation: str):
        self.__write_line(f"COPY {source} {destinsation}")
    
    def env(self, **kwargs: Dict[str, str]):
        for key, value in kwargs.items():
            self.__write_line(f"ENV {key}={value}")
    
    def run(self, run: str):
        self.__write_line(f"RUN {run}")
    
    def shell(self, *shell_args: Iterable[str]):
        shell_string = ", ".join(f'"{s}"' for s in shell_args)
        self.__write_line(f"SHELL [{shell_string}]")

    def user(self, user: str):
        self.__write_line(f"USER {user}")

    def workdir(self, workdir: str):
        self.__write_line(f"WORKDIR {workdir}")
