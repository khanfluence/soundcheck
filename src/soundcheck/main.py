import functools
import importlib.util
import inspect
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType
from typing import (
    Callable,
    Iterable,
    Iterator,
    List,
    NamedTuple,
    Optional,
    TextIO,
    Union,
)

import typer
from loguru import logger
from tinytag import TinyTag
from tinytag.tinytag import TinyTagException
from tqdm import tqdm

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
    with ThreadPoolExecutor() as executor:
        for file in tqdm(walk(lib_root), bar_format="Checked {n} files"):
            executor.submit(check_file, file, checks, lib_root)


def walk(path: os.PathLike) -> Iterator[os.DirEntry]:
    # Ignore type errors because of https://github.com/python/mypy/issues/3644
    for file in os.scandir(path):  # type: ignore
        if file.is_dir():
            yield from walk(file)
            continue
        yield file


def is_soundcheck_function(member: object) -> bool:
    # TODO: validate function takes Context and returns bool?
    return (
        inspect.isfunction(member)
        and hasattr(member, "__name__")
        and member.__name__.startswith("check_")
    )


@dataclass(init=False)
class SoundcheckContext:
    tag: TinyTag
    file_path: Path
    lib_root: Path

    def __init__(self, file: os.PathLike, tag: TinyTag, lib_root: os.PathLike) -> None:
        self.tag = tag
        self.file_path = Path(file).resolve()
        self.lib_root = Path(lib_root).resolve()


class Check(NamedTuple):
    name: str
    function: Callable[[SoundcheckContext], bool]


def get_checks(checks_module: Path) -> List[Check]:
    spec: Optional[ModuleSpec] = importlib.util.spec_from_file_location(
        "souncheck_checks_module", checks_module
    )
    if spec is None:
        message = f"Not a Python module: {checks_module}"
        logger.critical(message)
        raise ValueError(message)
    if spec.loader is None:
        message = f"Spec has no loader for module: {checks_module}"
        logger.critical(message)
        raise ValueError(message)
    module: ModuleType = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    checks: List[Check] = []
    for member in inspect.getmembers(module, is_soundcheck_function):
        checks.append(Check(member[0], member[1]))
        logger.trace(f"Found check function: {member[0]}")

    if len(checks) == 0:
        logger.warning("Found no check functions")

    return checks


def check_file(file: os.PathLike, checks: Iterable[Check], lib_root: os.PathLike):
    tag: TinyTag
    try:
        tag = TinyTag.get(file, image=True)
    except TinyTagException as exception:
        message: str = exception.args[0]
        if "no tag reader found to support filetype" in message.lower():
            logger.debug(f"Skipping unsupported file: {file}")
        else:
            logger.error(message)
        return

    context = SoundcheckContext(file=file, tag=tag, lib_root=lib_root)
    for check in checks:
        check.function(context)


class TyperExitError(typer.Exit):
    """An exception that indicates the application should exit with some status code
    and display a message."""

    def __init__(self, code: int, message: Optional[str] = None) -> None:
        self.message = message
        if message:
            if code:
                typer.echo("Error: ", nl=False, err=True)
            typer.echo(message, err=True)
        super().__init__(code=code)

    def __str__(self) -> str:
        string = f"[Exit status {self.exit_code}]"
        if self.message:
            string += f" {self.message}"
        return string
