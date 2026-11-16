# py-recursive-symlink

Resolve a path containing nested symlinks to its final real target, and raise a
distinct error when the chain contains a cycle or a dangling link.

```python
import os
import tempfile
from py_recursive_symlink import resolve, CycleError, DanglingSymlinkError

# Given a real file at /tmp/target.txt and a symlink /tmp/link.txt -> target.txt:
with tempfile.TemporaryDirectory() as tmp:
    target = os.path.join(tmp, "target.txt")
    with open(target, "w") as fh:
        fh.write("hello")
    link = os.path.join(tmp, "link.txt")
    os.symlink(target, link)

    final = resolve(link)
    print(final)  # /tmp/.../target.txt

    loop = os.path.join(tmp, "loop")
    os.symlink(loop, loop)
    try:
        resolve(loop)
    except CycleError as exc:
        print("cycle:", exc.cycle)
```

## Why this exists

`os.path.realpath` will happily return a path for a symlink cycle: it stops
following links after a fixed number of iterations and gives you *something*.
That is fine for display, but useless when you need to decide whether a path is
actually resolvable. This library walks the chain itself, keeps a set of every
path it has visited, and raises `CycleError` with the offending chain attached.
The trade-off is that it does not chase links inside intermediate path
components (for example `a/link/b` where `link` is a symlink); it only follows
the final component. That keeps the semantics easy to reason about and matches
the common case of a versioned `current` symlink.

## API

- `resolve(path: str) -> str` — returns an absolute, lexically normalised path.
  Raises `ResolutionError` if the path does not exist, `DanglingSymlinkError` if
a symlink points at a missing target, and `CycleError` if the chain repeats.
- `ResolutionError` — base class for the other two.
- `CycleError` — has a `.cycle` list of the paths traversed.
- `DanglingSymlinkError` — has `.link` and `.target` attributes.

## The awkward edge

A path that simply does not exist raises `ResolutionError`, not
`DanglingSymlinkError`. The distinction matters: a dangling symlink is a broken
link, while a missing path is just missing. If you catch `ResolutionError` you
cover both; catch `DanglingSymlinkError` only when you specifically care about
broken links.
