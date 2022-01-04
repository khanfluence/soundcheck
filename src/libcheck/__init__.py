import importlib.util
import inspect
import os
from dataclasses import dataclass
from importlib import import_module
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType
from typing import Callable, Iterator, List, NamedTuple, Optional

import typer
from loguru import logger
from tinytag import TinyTag
from tinytag.tinytag import TinyTagException

DEFAULT_CHECKS_MODULE_NAME = "libcheck.default_checks"


def walk(path: os.PathLike) -> Iterator[os.DirEntry]:
    # Ignore type errors because of https://github.com/python/mypy/issues/3644
    for file in os.scandir(path):  # type: ignore
        if file.is_dir():
            yield from walk(file)
            continue
        yield file


def is_libcheck_function(member: object) -> bool:
    # TODO: validate function takes Context and returns bool?
    return (
        inspect.isfunction(member)
        and hasattr(member, "__name__")
        and member.__name__.startswith("libcheck")
    )


@dataclass(init=False)
class LibcheckContext:
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
    func: Callable[[LibcheckContext], bool]
    # origin: str


# class CheckModule(NamedTuple):
#     module: ModuleType
#     name: str
#     origin: str


def get_checks(check_module_paths: Optional[List[Path]]) -> List[Check]:
    # TODO: skip duplicate modules
    modules: List[ModuleType] = []
    if check_module_paths:
        # user-specified
        for i, path in enumerate(check_module_paths):
            spec: Optional[ModuleSpec] = importlib.util.spec_from_file_location(
                f"libcheck_checks_module{i}", path
            )
            if spec is None:
                # TODO: log
                continue
            module: ModuleType = importlib.util.module_from_spec(spec)
            if spec.loader is None:
                # TODO: log
                continue
            spec.loader.exec_module(module)
            modules.append(module)
    else:
        # default
        try:
            modules.append(import_module(DEFAULT_CHECKS_MODULE_NAME))
        except ModuleNotFoundError:
            logger.critical("TODO")
            typer.Exit(1)

    checks: List[Check] = []
    for module in modules:
        module_checks: List[Check] = []
        for member in inspect.getmembers(module, is_libcheck_function):
            module_checks.append(Check(member[0], member[1]))

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
        #     f"Found libcheck functions {check_names} in module {module.__spec__.origin}"
        # )
    return checks


main = typer.Typer(add_completion=False)


# Pass context_settings to command instead of Typer
# because of https://github.com/tiangolo/typer/issues/208
@main.command(context_settings={"help_option_names": ["-h", "--help"]})
def libcheck(
    lib_root: Path = typer.Argument(
        Path(), exists=True, file_okay=False, readable=True, resolve_path=True
    ),
    check_modules: List[Path] = typer.Option(
        None,
        "--checks-module",
        "-m",
        exists=True,
        readable=True,
        resolve_path=True,
        help="Path to a Python module containing libcheck functions. Repeatable."
        " If none are specified, default checks are used.",
    ),
):
    checks: List[Check] = get_checks(check_modules)

    for file in walk(lib_root):
        tag: TinyTag
        try:
            tag = TinyTag.get(file, image=True)
        except TinyTagException as exc:
            msg: str = exc.args[0]
            if "no tag reader found to support filetype" in msg.lower():
                logger.debug(f"Skipping unsupported file: {file}")
            else:
                logger.error(msg)
            continue

        context = LibcheckContext(file=file, tag=tag, lib_root=lib_root)
        for check in checks:
            print(check.func(context))
