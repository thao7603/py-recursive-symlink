import os
import tempfile
import unittest
from pathlib import Path

from py_recursive_symlink import (
    CycleError,
    DanglingSymlinkError,
    ResolutionError,
    resolve,
)


class ResolveTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_plain_file_returns_absolute_path(self) -> None:
        target = self.root / "plain.txt"
        target.write_text("hello")
        self.assertEqual(resolve(str(target)), str(target))

    def test_relative_path_is_made_absolute(self) -> None:
        target = self.root / "plain.txt"
        target.write_text("hello")
        cwd = os.getcwd()
        try:
            os.chdir(self.root)
            self.assertEqual(resolve("plain.txt"), str(target))
        finally:
            os.chdir(cwd)

    def test_single_symlink_to_file(self) -> None:
        target = self.root / "target.txt"
        target.write_text("x")
        link = self.root / "link.txt"
        link.symlink_to(target)
        self.assertEqual(resolve(str(link)), str(target))

    def test_nested_symlinks(self) -> None:
        target = self.root / "target.txt"
        target.write_text("x")
        first = self.root / "first"
        second = self.root / "second"
        first.symlink_to(target)
        second.symlink_to(first)
        self.assertEqual(resolve(str(second)), str(target))

    def test_relative_symlink_target(self) -> None:
        target = self.root / "target.txt"
        target.write_text("x")
        link = self.root / "link.txt"
        link.symlink_to("target.txt")
        self.assertEqual(resolve(str(link)), str(target))

    def test_symlink_to_directory(self) -> None:
        target = self.root / "dir"
        target.mkdir()
        link = self.root / "dirlink"
        link.symlink_to(target)
        self.assertEqual(resolve(str(link)), str(target))

    def test_cycle_is_reported(self) -> None:
        a = self.root / "a"
        b = self.root / "b"
        a.symlink_to(b)
        b.symlink_to(a)
        with self.assertRaises(CycleError) as ctx:
            resolve(str(a))
        self.assertIn(str(a), ctx.exception.cycle)
        self.assertIn(str(b), ctx.exception.cycle)

    def test_self_cycle_is_reported(self) -> None:
        a = self.root / "a"
        a.symlink_to(a)
        with self.assertRaises(CycleError):
            resolve(str(a))

    def test_dangling_symlink_is_reported(self) -> None:
        link = self.root / "link"
        missing = self.root / "missing"
        link.symlink_to(missing)
        with self.assertRaises(DanglingSymlinkError) as ctx:
            resolve(str(link))
        self.assertEqual(ctx.exception.link, str(link))
        self.assertEqual(ctx.exception.target, str(missing))

    def test_missing_path_is_not_a_dangling_symlink(self) -> None:
        missing = self.root / "missing"
        with self.assertRaises(ResolutionError) as ctx:
            resolve(str(missing))
        self.assertNotIsInstance(ctx.exception, DanglingSymlinkError)

    def test_lexical_normalisation(self) -> None:
        target = self.root / "target.txt"
        target.write_text("x")
        link = self.root / "link.txt"
        link.symlink_to(target)
        messy = str(self.root / "sub" / ".." / "link.txt")
        self.assertEqual(resolve(messy), str(target))


if __name__ == "__main__":
    unittest.main()
