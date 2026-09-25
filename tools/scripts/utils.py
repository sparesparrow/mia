from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional, Sequence, Union


Command = Union[str, Sequence[str]]


@dataclass
class CommandResult:
    command: str
    returncode: int
    stdout: str
    stderr: str
    duration_s: float

    @property
    def succeeded(self) -> bool:
        return self.returncode == 0


def execute_command(
    command: Command,
    cwd: Optional[Path] = None,
    env: Optional[Mapping[str, str]] = None,
    timeout: Optional[int] = None,
    shell: Optional[bool] = None,
) -> CommandResult:
    command_text = command if isinstance(command, str) else " ".join(command)
    merged_env = os.environ.copy()
    if env:
        merged_env.update({key: str(value) for key, value in env.items()})

    use_shell = isinstance(command, str) if shell is None else shell
    started_at = time.monotonic()

    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            env=merged_env,
            shell=use_shell,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        returncode = completed.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        returncode = 124

    duration_s = round(time.monotonic() - started_at, 3)
    return CommandResult(
        command=command_text,
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        duration_s=duration_s,
    )


def create_whole_dir_path(path: Union[str, Path]) -> Path:
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory