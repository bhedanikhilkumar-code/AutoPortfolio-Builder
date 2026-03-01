from pathlib import Path
import sys

import typing_extensions as _typing_extensions

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


if not hasattr(_typing_extensions, "Sentinel"):
    class Sentinel:
        __slots__ = ("name",)

        def __init__(self, name: str) -> None:
            self.name = name

        def __repr__(self) -> str:
            return self.name


    _typing_extensions.Sentinel = Sentinel


if not hasattr(_typing_extensions, "NoExtraItems"):
    _typing_extensions.NoExtraItems = object()
