#!/usr/bin/env python3
"""symlib.merged: one symbol library that two generators fill.

    python3 generator/test_symlib.py [-v]        (Python 3.11 or later)
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import symlib  # noqa: E402


def lib(generator, *names):
    body = "".join('\t(symbol "%s"\n\t\t(in_bom yes)\n\t)\n' % n for n in names)
    return '(kicad_symbol_lib\n\t(version 20251024)\n\t(generator "%s")\n%s)\n' % (generator, body)


class Merged(unittest.TestCase):
    def test_a_library_one_generator_fills_is_unchanged(self):
        text = lib("opendap-kigen", "A")
        with mock.patch.object(symlib, "_render", return_value=None):
            self.assertEqual(symlib.merged("x", "opendap-kigen", text), text)

    def test_both_generators_write_the_same_file(self):
        k, b = lib("opendap-kigen", "RK809-5"), lib("opendap-bga", "RK3566")
        with mock.patch.object(symlib, "_render", return_value=b):
            from_kigen = symlib.merged("rockchip", "opendap-kigen", k)
        with mock.patch.object(symlib, "_render", return_value=k):
            from_bga = symlib.merged("rockchip", "opendap-bga", b)
        self.assertEqual(from_kigen, from_bga)
        self.assertEqual(from_kigen, lib("opendap-bga", "RK3566", "RK809-5"))

    def test_a_symbol_drawn_twice_is_an_error(self):
        with mock.patch.object(symlib, "_render", return_value=lib("opendap-bga", "A")):
            with self.assertRaises(ValueError):
                symlib.merged("x", "opendap-kigen", lib("opendap-kigen", "A"))

    def test_the_repository_libraries_round_trip(self):
        symbols = os.path.join(os.path.dirname(os.path.abspath(symlib.__file__)), "..", "symbols")
        for path in sorted(p for p in os.listdir(symbols) if p.endswith(".kicad_sym")):
            text = open(os.path.join(symbols, path)).read()
            head, blocks = symlib.split(text)
            self.assertEqual("\n".join(head + [l for _, b in blocks for l in b] + [")"]) + "\n", text, path)


if __name__ == "__main__":
    unittest.main()
