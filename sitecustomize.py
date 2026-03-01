"""Local compatibility hooks for constrained Python environments."""

import typing_extensions as _typing_extensions


if not hasattr(_typing_extensions, "Sentinel"):
    class Sentinel:
        """Fallback for typing_extensions.Sentinel on older installs."""

        __slots__ = ("name",)

        def __init__(self, name: str) -> None:
            self.name = name

        def __repr__(self) -> str:
            return self.name


    _typing_extensions.Sentinel = Sentinel


if not hasattr(_typing_extensions, "NoExtraItems"):
    _typing_extensions.NoExtraItems = object()
