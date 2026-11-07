"""验证负地址数组、字符帧和阶段二三题；参考计算只用于测试端。"""

from collections import Counter
from contextlib import redirect_stdout
from io import StringIO
import random
import unittest
from unittest.mock import patch

from tools.arrays import NegativeArray
from tools.macros import Macros, compile_program, seq
from tools.runtime import ROOT, Runtime, build, problem
from tools.stage2 import PROGRAMS, make_code


def execute(ir, stdin):
    rt = Runtime(can_direct_addressing=False)
    output = StringIO()
    with patch("sys.stdin", StringIO(stdin)), redirect_stdout(output):
        rt.run(ir)
    return output.getvalue(), rt


def frame(text):
    return f"{len(text)}\n{text}"


def reference_rot13(text):
    source = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    target = "NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm"
    return text.translate(str.maketrans(source, target))


def reference_wc(text):
    inside = False
    words = 0
    for char in text:
        if char in "\t\n\v\f\r ":
            inside = False
        elif not inside:
            words += 1
            inside = True
    return f"{text.count(chr(10))} {words} {len(text)}\n"


class ArrayTests(unittest.TestCase):
    def test_array_write_read_zero_overwrite_and_pointer_reset(self):
        def program(m):
            array = NegativeArray(m)
            parts = [array.reset()]
            for value in [0, 255, 1, 0, 11]:
                parts += [array.put(f"&{value}"), array.advance()]
            parts += [array.reset(), array.put("&42"), array.put("&0"), array.reset()]
            for _ in range(5):
                parts += [array.read() + " @print", array.advance()]
            return seq(*parts)

        output, _ = execute(build(compile_program(program)), "")
        self.assertEqual(output, "0\n255\n1\n0\n11\n")

    def test_seek_and_in_place_updates_preserve_other_elements(self):
        def program(m):
            array = NegativeArray(m)
            index = m.slot("测试下标")
            parts = []
            for value in [0, 255, 1, 255, 0, 7]:
                parts += [m.constant(index, value), array.seek(index), array.change("@+")]
            parts += [m.constant(index, 0), array.seek(index), array.change("@-"), array.change("@-")]
            for value in [0, 1, 2, 7, 255]:
                parts += [m.constant(index, value), array.seek(index), array.read() + " @print"]
            return seq(*parts)

        output, _ = execute(build(compile_program(program)), "")
        self.assertEqual(output, "0\n1\n0\n1\n2\n")


class Stage2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code = {name: make_code(name) for name in PROGRAMS}
        cls.ir = {name: build(code) for name, code in cls.code.items()}

    def test_generated_operations_are_standard(self):
        for name, code in self.code.items():
            with self.subTest(problem=name):
                operations = {token for token in code.split() if token.startswith("@")}
                self.assertLessEqual(operations, {"@input", "@input_as_char", "@print_as_char", "@+", "@-"})
                self.assertEqual(code, make_code(name))
                directory = ROOT / problem(name)["directory"]
                self.assertEqual(code, (directory / "solution.pp3").read_text(encoding="ascii"))

    def test_rot13_all_256_codes_and_involution(self):
        text = "".join(map(chr, range(256)))
        output, _ = execute(self.ir["P006"], frame(text))
        self.assertEqual(output, reference_rot13(text))
        restored, _ = execute(self.ir["P006"], frame(output))
        self.assertEqual(restored, text)

    def test_rot13_examples_and_empty_frames(self):
        for text in ["", "Hello, World!", "ANZanz", "[\\]^_`", "a\nB\n", "\x00\xff", "12345!?", "\n"]:
            with self.subTest(text=text):
                output, _ = execute(self.ir["P006"], frame(text))
                self.assertEqual(output, reference_rot13(text))

    def test_sort_all_256_codes_and_duplicates(self):
        text = "".join(map(chr, reversed(range(256)))) + "\x00\xff\x00\x80\x80"
        output, _ = execute(self.ir["P007"], frame(text))
        self.assertEqual(output, "".join(sorted(text)))
        self.assertEqual(Counter(output), Counter(text))

    def test_sort_examples(self):
        for text in ["", "AAAA", "abc", "cba", "\x00", "\xff", "b\na", "\n\n\n", "\x00A\x00A"]:
            with self.subTest(text=text):
                output, _ = execute(self.ir["P007"], frame(text))
                self.assertEqual(output, "".join(sorted(text)))

    def test_sort_duplicate_count_is_not_limited_to_one_byte(self):
        text = "A" * 300 + "\x00" * 270 + "\xff" * 260
        output, _ = execute(self.ir["P007"], frame(text))
        self.assertEqual(output, "".join(sorted(text)))
        self.assertEqual(Counter(output), Counter(text))

    def test_wc_ascii_whitespace_and_non_ascii_non_whitespace(self):
        samples = ["", "abc", "abc\n", "\n\n", "a b\tc\nd\ve\ff\rg", "a\xa0b", "\t \r",
                   "\x00\xff", "first\nsecond", " a  b "]
        for text in samples:
            with self.subTest(text=text):
                output, _ = execute(self.ir["P008"], frame(text))
                self.assertEqual(output, reference_wc(text))

    def test_wc_all_byte_code_points(self):
        text = "".join(map(chr, range(256)))
        output, _ = execute(self.ir["P008"], frame(text))
        self.assertEqual(output, reference_wc(text))

    def test_wc_counters_greater_than_255(self):
        text = "A\n" * 300
        output, _ = execute(self.ir["P008"], frame(text))
        self.assertEqual(output, "300 300 600\n")

    def test_negative_length_errors_before_character_input(self):
        for name in PROGRAMS:
            for length in [-1, -15, -64, -300]:
                with self.subTest(problem=name, length=length):
                    output, rt = execute(self.ir[name], f"{length}\n")
                    self.assertEqual(output, "ERROR\n")
                    self.assertEqual(list(rt.std_register["input_as_char"].buffer), [])

    def test_unicode_outside_byte_range_errors_without_partial_output(self):
        for name in PROGRAMS:
            for text in ["中", "AB中", "😀A", "A\u0100Z"]:
                with self.subTest(problem=name, text=text):
                    output, _ = execute(self.ir[name], frame(text))
                    self.assertEqual(output, "ERROR\n")

    def test_invalid_frame_is_fully_consumed_before_error(self):
        for name in PROGRAMS:
            with self.subTest(problem=name):
                output, rt = execute(self.ir[name], "3\nA中Btail\n")
                self.assertEqual(output, "ERROR\n")
                self.assertEqual("".join(rt.std_register["input_as_char"].buffer), "tail\n")

    def test_premature_eof_preserves_exception_without_partial_output(self):
        for name in PROGRAMS:
            for stdin in ["1\n", "4\nAB", "4\nA中"]:
                with self.subTest(problem=name, stdin=stdin):
                    output = StringIO()
                    with patch("sys.stdin", StringIO(stdin)), redirect_stdout(output), self.assertRaises(EOFError):
                        Runtime(can_direct_addressing=False).run(self.ir[name])
                    self.assertEqual(output.getvalue(), "")

    def test_synthetic_lf_counts_toward_length(self):
        for name, expected in [("P006", "NO\n"), ("P007", "\nAB"), ("P008", "1 1 3\n")]:
            with self.subTest(problem=name):
                output, _ = execute(self.ir[name], "3\nAB")
                self.assertEqual(output, expected)

    def test_characters_beyond_frame_remain_buffered(self):
        for name in PROGRAMS:
            with self.subTest(problem=name):
                _, rt = execute(self.ir[name], "2\nABextra\n")
                self.assertEqual("".join(rt.std_register["input_as_char"].buffer), "extra\n")

    def test_unicode_outside_frame_does_not_cause_error(self):
        for name, expected in [("P006", "N"), ("P007", "A"), ("P008", "0 1 1\n")]:
            with self.subTest(problem=name):
                output, rt = execute(self.ir[name], "1\nA中\n")
                self.assertEqual(output, expected)
                self.assertEqual("".join(rt.std_register["input_as_char"].buffer), "中\n")

    def test_zero_length_does_not_read_characters(self):
        for name, expected in [("P006", ""), ("P007", ""), ("P008", "0 0 0\n")]:
            with self.subTest(problem=name):
                output, rt = execute(self.ir[name], "0\n")
                self.assertEqual(output, expected)
                self.assertEqual(list(rt.std_register["input_as_char"].buffer), [])

    def test_reproducible_random_frames(self):
        rng = random.Random(20261107)
        samples = ["".join(chr(rng.randrange(256)) for _ in range(rng.randrange(50))) for _ in range(24)]
        for name, oracle in [("P006", reference_rot13), ("P007", lambda text: "".join(sorted(text))), ("P008", reference_wc)]:
            for index, text in enumerate(samples):
                with self.subTest(problem=name, index=index):
                    output, _ = execute(self.ir[name], frame(text))
                    self.assertEqual(output, oracle(text))

    def test_length_syntax_uses_unmodified_standard_input(self):
        for name in PROGRAMS:
            for stdin, exception in [("", EOFError), ("abc\n", ValueError)]:
                with self.subTest(problem=name, stdin=stdin):
                    output = StringIO()
                    with patch("sys.stdin", StringIO(stdin)), redirect_stdout(output), self.assertRaises(exception):
                        Runtime(can_direct_addressing=False).run(self.ir[name])
                    self.assertEqual(output.getvalue(), "")

    def test_standard_length_whitespace_plus_and_negative_zero(self):
        for name, expected in [("P006", "NO"), ("P007", "AB"), ("P008", "0 1 2\n")]:
            with self.subTest(problem=name):
                output, _ = execute(self.ir[name], "  +0002  \nAB")
                self.assertEqual(output, expected)
        for name, expected in [("P006", ""), ("P007", ""), ("P008", "0 0 0\n")]:
            with self.subTest(problem=name):
                output, _ = execute(self.ir[name], "-0\n")
                self.assertEqual(output, expected)

    def test_reused_ir_keeps_different_runtime_buffers_separate(self):
        for name, oracle in [("P006", reference_rot13), ("P007", lambda text: "".join(sorted(text))), ("P008", reference_wc)]:
            first = Runtime(can_direct_addressing=False)
            second = Runtime(can_direct_addressing=False)
            with patch("sys.stdin", StringIO("2\nABfirst\n")), redirect_stdout(StringIO()) as output:
                first.run(self.ir[name])
            self.assertEqual(output.getvalue(), oracle("AB"))
            with patch("sys.stdin", StringIO("2\nXYsecond\n")), redirect_stdout(StringIO()) as output:
                second.run(self.ir[name])
            self.assertEqual(output.getvalue(), oracle("XY"))
            self.assertEqual("".join(first.std_register["input_as_char"].buffer), "first\n")
            self.assertEqual("".join(second.std_register["input_as_char"].buffer), "second\n")

    def test_array_contents_and_regular_slots_keep_their_invariants(self):
        for name in PROGRAMS:
            layout = Macros()
            PROGRAMS[name](layout)
            bound = len(layout.slots) + 3
            pointer = layout.slots.get("数据区.指针")
            references = {slot for key, slot in layout.slots.items()
                          if key.endswith((".表头", ".表尾", ".未使用地址", ".转移节点")) or key == "排序节点"}
            text = "z\x00A\xffz\n"
            _, rt = execute(self.ir[name], frame(text))
            with self.subTest(problem=name):
                for address, value in rt.memory.items():
                    if address == 0:
                        continue
                    if address in (-1, -2):
                        self.assertEqual(value, 0)
                        continue
                    if address == pointer:
                        self.assertLessEqual(value, -bound)
                    elif address in references:
                        self.assertTrue(value == 0 or value <= -bound)
                        if value:
                            self.assertEqual(rt.memory[value], 0)
                    elif address <= -bound and name == "P007":
                        field = (-bound - address) % 4
                        if field == 0:
                            self.assertEqual(value, 0)
                        elif field == 3:
                            self.assertTrue(value == 0 or (value <= -bound and (-bound - value) % 4 == 0))
                        else:
                            self.assertGreaterEqual(value, 0)
                    elif address <= -bound:
                        self.assertGreaterEqual(value, 0)
                    elif address < 0:
                        self.assertGreaterEqual(value, 0)
                    else:
                        self.assertEqual(value, 0)
                if name == "P006":
                    self.assertEqual("".join(chr(rt.memory[-bound - index]) for index in range(len(text))), reference_rot13(text))
                elif name == "P007":
                    nodes = [-bound - 4 * index for index in range(len(text))]
                    self.assertEqual([rt.memory[node - 1] for node in nodes], list(map(ord, text)))
                    self.assertTrue(all(rt.memory[node] == rt.memory[node - 3] == 0 for node in nodes))
                    self.assertEqual(rt.memory[layout.slots["排序数据.表头"]], 0)
                    self.assertEqual(rt.memory[layout.slots["排序数据.表尾"]], 0)


if __name__ == "__main__":
    unittest.main()
