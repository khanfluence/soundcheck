# import importlib.util
import inspect
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
from importlib import import_module
from importlib.metadata import version

# from importlib.machinery import ModuleSpec
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

from soundcheck.util import TyperExitError

logger.remove()

__version__ = version(__name__)

DEFAULT_CHECKS_MODULE_NAME = "soundcheck.default_checks"


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
    lib_root: Path
    rel_path: Path
    abs_path: Path

    def __init__(self, file: os.PathLike, tag: TinyTag, lib_root: os.PathLike) -> None:
        self.tag = tag
        self.abs_path = Path(file).resolve()
        self.lib_root = Path(lib_root).resolve()
        self.rel_path = self.abs_path.relative_to(lib_root)


class Check(NamedTuple):
    name: str
    func: Callable[[SoundcheckContext], bool]
    # origin: str


# class CheckModule(NamedTuple):
#     module: ModuleType
#     name: str
#     origin: str


# def get_checks(check_module_paths: Optional[List[Path]]) -> List[Check]:
def get_checks() -> List[Check]:
    # TODO: skip duplicate modules
    modules: List[ModuleType] = []
    # if check_module_paths:
    #     # user-specified
    #     for i, path in enumerate(check_module_paths):
    #         spec: Optional[ModuleSpec] = importlib.util.spec_from_file_location(
    #             f"soundcheck_checks_module{i}", path
    #         )
    #         if spec is None:
    #             # TODO: log
    #             continue
    #         module: ModuleType = importlib.util.module_from_spec(spec)
    #         if spec.loader is None:
    #             # TODO: log
    #             continue
    #         spec.loader.exec_module(module)
    #         modules.append(module)
    # else:
    # default
    try:
        modules.append(import_module(DEFAULT_CHECKS_MODULE_NAME))
    except ModuleNotFoundError:
        logger.critical("TODO")
        typer.Exit(1)

    checks: List[Check] = []
    for module in modules:
        # module_checks: List[Check] = []
        for member in inspect.getmembers(module, is_soundcheck_function):
            # module_checks.append(Check(member[0], member[1]))
            checks.append(Check(member[0], member[1]))

        # TODO: if feasible, log functions found per-module
        # sort out module_name crap
        # check_names: List[str] = [check.name for check in module_checks]
        # if (
        #     module.__spec__ is not None
        #     and module.__spec__.name == DEFAULT_CHECKS_MODULE_NAME
        # ):
        #     module_name = DEFAULT_CHECKS_MODULE_NAME
        # else:
        #     module_name = module.__spec__.origin
        # module_name: str = DEFAULT_CHECKS_MODULE_NAME if module.__spec__.name else ""
        # logger.trace(
        #     f"Found soundcheck functions {check_names} in module {module.__spec__.origin}"
        # )
    return checks


def check_file(file: os.PathLike, checks: Iterable[Check], lib_root: os.PathLike):
    tag: TinyTag
    try:
        tag = TinyTag.get(file, image=True)
    except TinyTagException as exc:
        msg: str = exc.args[0]
        if "no tag reader found to support filetype" in msg.lower():
            logger.debug(f"Skipping unsupported file: {file}")
        else:
            logger.error(msg)
        return

    context = SoundcheckContext(file=file, tag=tag, lib_root=lib_root)
    for check in checks:
        # print(check.func(context))
        check.func(context)


main = typer.Typer(add_completion=False)


def show_version(version: bool) -> bool:
    if version:
        raise TyperExitError(0, f"{__name__} {__version__}")
    return version


class LogLevel(str, Enum):
    TRACE = "trace"
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# Pass context_settings to command instead of Typer
# because of https://github.com/tiangolo/typer/issues/208
@main.command(context_settings={"help_option_names": ["-h", "--help"]})
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
    # check_modules: List[Path] = typer.Option(
    #     None,
    #     "--checks-module",
    #     "-m",
    #     exists=True,
    #     readable=True,
    #     resolve_path=True,
    #     help="Path to a Python module containing soundcheck functions. Repeatable."
    #     " If not specified, default checks are used.",
    # ),
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

    # checks: List[Check] = get_checks(check_modules)
    checks: List[Check] = get_checks()
    with ThreadPoolExecutor(max_workers=8) as executor:
        for file in tqdm(walk(lib_root), bar_format="Checked {n} files"):
            executor.submit(check_file, file, checks, lib_root)
        # check_file(file, checks, lib_root)