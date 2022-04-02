import functools
import os
import queue
import sys
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from pathlib import Path
from typing import Iterator, List, Optional, TextIO, Union

import typer
from loguru import logger
from tqdm import tqdm

from soundcheck.check import Check, check_file, get_checks
from soundcheck.version import __version__

main = typer.Typer(add_completion=False)


def show_version(version: bool) -> bool:
    if version:
        raise TyperExitError(0, __version__)
    return version


class LogLevel(str, Enum):
    TRACE = "trace"
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


def handle_exceptions(function):
    @functools.wraps(function)
    def inner(*args, **kwargs):
        try:
            function(*args, **kwargs)
        except ValueError as exception:
            raise TyperExitError(1, str(exception))

    return inner


# Pass context_settings to command instead of Typer
# because of https://github.com/tiangolo/typer/issues/208
@main.command(context_settings={"help_option_names": ["-h", "--help"]})
@handle_exceptions
def soundcheck(
    lib_root: Path = typer.Option(
        Path(),
        "--library",
        "-l",
        exists=True,
        file_okay=False,
        readable=True,
        resolve_path=True,
    ),
    checks_module: Path = typer.Option(
        ...,
        "--checks-module",
        "-m",
        exists=True,
        readable=True,
        resolve_path=True,
        help="Path to a Python module containing soundcheck functions.",
    ),
    fail_fast: bool = typer.Option(
        False,
        "--fail-fast/--allow-fail",
        "-f/-F",
        show_default=True,
        help="Exit when a test fails.",
    ),
    log_level: Optional[LogLevel] = typer.Option(
        None,
        case_sensitive=False,
        help="Log messages of at least this importance.",
    ),
    log_file: Optional[Path] = typer.Option(
        None,
        dir_okay=False,
        writable=True,
        help="Log to this file instead of stderr.",
    ),
    _version: bool = typer.Option(
        False,
        "--version",
        "-v",
        is_eager=True,
        callback=show_version,
        help="Show the version and exit.",
        show_default=False,
    ),
):
    if log_level:
        sink: Union[Path, TextIO] = log_file or sys.stderr
        logger.add(sink, level=log_level.upper())

    checks: List[Check] = get_checks(checks_module)
    result_queue: queue.Queue = queue.Queue()
    with ThreadPoolExecutor() as executor:
        for file in tqdm(walk(lib_root), bar_format="Checked {n} files"):
            executor.submit(check_file, file, checks, lib_root, result_queue)

            # This probably trips fairly often, but I don't know a better way
            try:
                result = result_queue.get(block=False)
            except queue.Empty:
                continue
            else:
                process_result(result, fail_fast)

    while not result_queue.empty():
        result = result_queue.get()
        process_result(result, fail_fast)


def process_result(result, fail_fast: bool) -> None:
    print(result)
    if result["status"] == "fail":
        # TODO: log?
        if fail_fast:
            raise TyperExitError(1, "TODO: failure")


def walk(path: os.PathLike) -> Iterator[os.DirEntry]:
    # Ignore type errors because of https://github.com/python/mypy/issues/3644
    for file in os.scandir(path):  # type: ignore
        if file.is_dir():
            yield from walk(file)
            continue
        yield file


class TyperExitError(typer.Exit):
    """An exception that indicates the application should exit with some status code
    and display a message."""

    def __init__(self, code: int, message: Optional[str] = None) -> None:
        self.message = message

        if message:
            fmt_message = message
            if code:
                fmt_message = "Error: " + fmt_message
            typer.echo(fmt_message, err=True)

        super().__init__(code=code)

    def __str__(self) -> str:
        string = f"[Exit status {self.exit_code}]"
        if self.message:
            string += f" {self.message}"
        return string
