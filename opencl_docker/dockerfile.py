from io import StringIO
from typing import Iterable, Dict

class Dockerfile:
    def __init__(self, image: str):
        self.image = image
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

    def copy(self, source: str, destination: str = "", src_img: str = "", destinsation: str = ""):
        dest = destination or destinsation
        if src_img:
            self.__write_line(f"COPY --from={src_img} {source} {dest}")
        else:
            self.__write_line(f"COPY {source} {dest}")
    
    def env(self, **kwargs: Dict[str, str]):
        for key, value in kwargs.items():
            self.__write_line(f"ENV {key}={value}")
    
    def run(self, run: str):
        self.__write_line(f"RUN {run}")
    
    def shell(self, *shell_args: Iterable[str]):
        shell_string = ", ".join(f'"{s}"' for s in shell_args)
        self.__write_line(f"SHELL [{shell_string}]")

    def user(self, user: str):
        self.__write_line(f"RUN id -u {user} >/dev/null 2>&1 || useradd -ms /bin/bash {user}")
        # self.__write_line(f"RUN groupadd -g 65533 cuda && usermod -a -G cuda {user}") # needed for waiter
        self.__write_line(f"USER {user}")

    def userswitch(self, user: str):
        self.__write_line(f"USER {user}")

    def workdir(self, workdir: str):
        self.__write_line(f"WORKDIR {workdir}")

    def volume(self, *volumes: str):
        vol_string = ", ".join(f'"{v}"' for v in volumes)
        self.__write_line(f"VOLUME [{vol_string}]")

    def entrypoint(self, *ep_args: str):
        ep_string = ", ".join(f'"{e}"' for e in ep_args)
        self.__write_line(f"ENTRYPOINT [{ep_string}]")
