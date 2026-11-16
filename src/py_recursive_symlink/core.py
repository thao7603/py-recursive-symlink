"""Resolve nested symlinks to a final real target, detecting cycles.

This module deliberately does not use :func:`os.path.realpath` because
``realpath`` silently collapses cycles to *some* path without telling the
caller that a cycle existed.  Callers that need to know whether a path is
resolvable at all (for example, a backup tool deciding whether it can follow
a link) need that information, so we walk the chain ourselves.
"""

from __future__ import annotations

import os
from typing import List, Set


class ResolutionError(Exception):
    """Base class for every failure raised by :func:`resolve`."""


class CycleError(ResolutionError):
    """Raised when following a symlink revisits a path already seen.

    ``cycle`` holds the offending chain, in the order it was traversed.
    """

    def __init__(self, cycle: List[str]) -> None:
        self.cycle = list(cycle)
        super().__init__("symlink cycle: " + " -> ".join(self.cycle))


class DanglingSymlinkError(ResolutionError):
    """Raised when a symlink points at a path that does not exist."""

    def __init__(self, link: str, target: str) -> None:
        self.link = link
        self.target = target
        super().__init__(f"dangling symlink {link!r} -> {target!r}")


def _canonical(path: str) -> str:
    """Return an absolute, lexically normalised form of *path*.

    We normalise with :func:`os.path.normpath` rather than
    :func:`os.path.realpath` on purpose: ``realpath`` would resolve symlinks
    for us, which is exactly the work this module is doing, and it would hide
    cycles instead of reporting them.
    """
    return os.path.normpath(os.path.abspath(path))


def resolve(path: str) -> str:
    """Follow *path* through any chain of symlinks and return the real target.

    The returned path is absolute and lexically normalised.  A path that is
    not a symlink is returned unchanged (apart from normalisation); the
    function never touches the filesystem beyond ``os.lstat`` and
    ``os.readlink``.

    Raises :class:`CycleError` if the chain revisits a path, and
    :class:`DanglingSymlinkError` if a link points at a missing target.
    """
    current = _canonical(path)
    seen: Set[str] = set()
    chain: List[str] = []

    while True:
        if current in seen:
            chain.append(current)
            raise CycleError(chain)
        seen.add(current)
        chain.append(current)

        try:
            st = os.lstat(current)
        except FileNotFoundError as exc:
            # The very first path may simply not exist.  That is not a
            # dangling symlink: there was no link to dangle.  We still raise,
            # because returning a path that does not exist would be a lie.
            if len(chain) == 1:
                raise ResolutionError(f"path does not exist: {current!r}") from exc
            previous = chain[-2]
            raise DanglingSymlinkError(previous, current) from exc

        if not os.path.islink(current):
            return current

        target = os.readlink(current)
        if not os.path.isabs(target):
            target = os.path.join(os.path.dirname(current), target)
        current = _canonical(target)
