import importlib.util
import inspect
import os
import queue
from dataclasses import dataclass
from importlib.machinery import ModuleSpec
from pathlib import Path
from types import ModuleType
from typing import Callable, Iterable, List, NamedTuple, Optional

from loguru import logger
from tinytag import TinyTag
from tinytag.tinytag import TinyTagException


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
    module_path: Path
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
        checks.append(Check(checks_module, member[1]))
        logger.trace(f"Found check function: {member[0]}")

    if len(checks) == 0:
        logger.warning("Found no check functions")

    return checks


def is_soundcheck_function(member: object) -> bool:
    # TODO: validate function takes Context and returns bool?
    return (
        inspect.isfunction(member)
        and hasattr(member, "__name__")
        and member.__name__.startswith("check_")
    )


def check_file(
    file: os.PathLike,
    checks: Iterable[Check],
    lib_root: os.PathLike,
    result_queue: queue.Queue,
):
    tag: TinyTag
    try:
        tag = TinyTag.get(file, image=True)
    except TinyTagException as exception:
        message: str = exception.args[0]
        if "no tag reader found to support filetype" in message.lower():
            logger.trace(f"Skipping unsupported file: {file}")
        else:
            logger.error(message)
        return

    context = SoundcheckContext(file=file, tag=tag, lib_root=lib_root)
    for check in checks:
        result = {
            "check": f"{check.module_path}.{check.function.__name__}",
            "file": str(Path(file)),
        }
        try:
            check.function(context)
        except AssertionError:
            result["status"] = "fail"
        else:
            result["status"] = "pass"
        finally:
            result_queue.put(result)
