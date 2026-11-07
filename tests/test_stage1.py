"""阶段一静态宏、数字字符编解码、乘法与 GCD 的独立验证。"""

from contextlib import redirect_stdout
from io import StringIO
import math
import random
import unittest
from unittest.mock import patch

from pp3_toolkit import Macros, compile_program, seq
from tools.runtime import ROOT, Runtime, build, problem
from tools.stage1 import PROGRAMS, make_code


def evaluate(ir, stdin):
    output = StringIO()
    with patch("sys.stdin", StringIO(stdin)), redirect_stdout(output):
        Runtime(can_direct_addressing=False).run(ir)
    return output.getvalue()


class MacroTests(unittest.TestCase):
    def test_self_loop_update_handles_zero_and_both_directions(self):
        for value in [0, 1, 2, 100, 10**100]:
            for operation, expected in [("@+", value + 1), ("@-", value - 1)]:
                if expected == -1:
                    continue
                with self.subTest(value=value, operation=operation):
                    m = Macros()
                    x = m.slot("数值")
                    code = seq(m.constant(x, value), m.change(x, operation), m.read(x) + " @print")
                    self.assertEqual(evaluate(build(code), ""), f"{expected}\n")

    def test_unsigned_division_matches_python(self):
        m = Macros()
        a, b, q, r = (m.slot(name) for name in ["分子", "分母", "商", "余数"])
        code = seq(m.put(a, "@input"), m.put(b, "@input"), m.divmod_unsigned(a, b, q, r),
                   m.read(q) + " @print", m.read(r) + " @print")
        ir = build(code)
        for numerator in range(31):
            for denominator in range(1, 13):
                with self.subTest(numerator=numerator, denominator=denominator):
                    quotient, remainder = divmod(numerator, denominator)
                    self.assertEqual(evaluate(ir, f"{numerator}\n{denominator}\n"), f"{quotient}\n{remainder}\n")

    def test_unsigned_character_output_matches_decimal(self):
        m = Macros()
        value = m.slot("原数")
        code = seq(m.put(value, "@input"), m.print_unsigned_decimal(value))
        ir = build(code)
        for value in [0, 1, 9, 10, 11, 99, 100, 101, 999, 1000, 12345]:
            with self.subTest(value=value):
                self.assertEqual(evaluate(ir, f"{value}\n"), str(value))

    def test_signed_decoder_covers_its_own_reserved_range(self):
        def program(m):
            value, sign = m.slot("测试幅值"), m.slot("测试符号")
            return seq(m.decode_integer(value, sign), m.read(value) + " @print", m.read(sign) + " @print")

        ir = build(compile_program(program))
        for value in range(-60, 61):
            with self.subTest(value=value):
                self.assertEqual(evaluate(ir, f"{value}\n"), f"{abs(value)}\n{int(value < 0)}\n")

    def test_decoder_reuses_slots_and_handles_expanded_layout(self):
        def program(m):
            a, sa, b, sb = (m.slot(name) for name in ("甲幅值", "甲符号", "乙幅值", "乙符号"))
            # 保留槽位随程序扩大；所有槽含自然数，输入仍可能与任一槽地址相等。
            padding = [m.constant(m.slot(f"额外槽{i}"), i) for i in range(80)]
            return seq(*padding, m.decode_integer(a, sa), m.decode_integer(b, sb),
                       m.read(a) + " @print", m.read(sa) + " @print",
                       m.read(b) + " @print", m.read(sb) + " @print")

        ir = build(compile_program(program))
        for a in [-500, -100, -88, -87, -86, -85, -84, -83, -82, -81, -2, -1, 0, 1, 83, 500]:
            for b in [-90, -89, -88, -87, 0, 88]:
                with self.subTest(a=a, b=b):
                    self.assertEqual(evaluate(ir, f"{a}\n{b}\n"),
                                     f"{abs(a)}\n{int(a < 0)}\n{abs(b)}\n{int(b < 0)}\n")

    def test_comparison_restores_markers_and_preserves_inputs(self):
        def program(m):
            a, b, lt, eq, gt = (m.slot(name) for name in ("甲", "乙", "小于", "等于", "大于"))
            return seq(m.put(a, "@input"), m.put(b, "@input"), m.compare(a, b, lt, eq, gt),
                       *(m.read(slot) + " @print" for slot in (a, b, lt, eq, gt)))

        ir = build(compile_program(program))
        for a, b in [(0, 0), (0, 255), (255, 0), (57, 48), (48, 57), (300, 301), (10**100, 10**100)]:
            rt = Runtime(can_direct_addressing=False)
            with patch("sys.stdin", StringIO(f"{a}\n{b}\n")), redirect_stdout(StringIO()) as output:
                rt.run(ir)
            self.assertEqual(output.getvalue(), f"{a}\n{b}\n{int(a < b)}\n{int(a == b)}\n{int(a > b)}\n")
            self.assertTrue(all(value == 0 for address, value in rt.memory.items() if address > 0))
            self.assertEqual((rt.memory[-1], rt.memory[-2]), (0, 0))


class Stage1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code = {problem_id: make_code(problem_id) for problem_id in PROGRAMS}
        cls.ir = {problem_id: build(code) for problem_id, code in cls.code.items()}

    def test_generation_is_deterministic(self):
        for problem_id in PROGRAMS:
            with self.subTest(problem=problem_id):
                self.assertEqual(self.code[problem_id], make_code(problem_id))
                directory = ROOT / problem(problem_id)["directory"]
                self.assertEqual(self.code[problem_id], (directory / "solution.pp3").read_text(encoding="ascii"))

    def test_decimal_codec_uses_only_character_io(self):
        operations = {token for token in self.code["P003"].split() if token.startswith("@")}
        self.assertEqual(operations, {"@input_as_char", "@print_as_char", "@+", "@-"})

    def test_decimal_valid_inputs(self):
        values = ["0", "-0", "+0", "00000", "-000", "+0012", "-0012", "12345", "-9999",
                  "0" * 80 + "123", "-" + "0" * 80 + "123", "7"]
        for text in values:
            for ending in ["\n", ""]:
                with self.subTest(text=text, ending=ending):
                    self.assertEqual(evaluate(self.ir["P003"], text + ending), f"{int(text)}\n")

    def test_decimal_invalid_inputs(self):
        values = ["", "+", "-", " ", " 12", "12 ", "1 2", "++1", "--1", "+-1", "1-2",
                  "1.2", "0x10", "1_000", "12a3", "a123", "１２", "中", "\x00", "1\t2"]
        for text in values:
            with self.subTest(text=text):
                self.assertEqual(evaluate(self.ir["P003"], text + "\n"), "ERROR\n")

    def test_decimal_stops_after_one_line(self):
        self.assertEqual(evaluate(self.ir["P003"], "12\n34\n"), "12\n")

    def test_decimal_eof_before_any_input_propagates(self):
        with patch("sys.stdin", StringIO("")), redirect_stdout(StringIO()), self.assertRaises(EOFError):
            Runtime(can_direct_addressing=False).run(self.ir["P003"])

    def test_decimal_reproducible_numeric_variants(self):
        rng = random.Random(303)
        for _ in range(30):
            value = rng.randint(-3000, 3000)
            prefix = "-" if value < 0 else rng.choice(["", "+"])
            text = prefix + "0" * rng.randrange(5) + str(abs(value))
            with self.subTest(text=text):
                self.assertEqual(evaluate(self.ir["P003"], text + "\n"), f"{value}\n")

    def test_standard_arithmetic_operations_only(self):
        allowed = {"@input", "@print", "@print_as_char", "@+", "@-"}
        for problem_id in ("P004", "P005"):
            with self.subTest(problem=problem_id):
                self.assertLessEqual({token for token in self.code[problem_id].split() if token.startswith("@")}, allowed)

    def test_finished_memory_respects_the_address_invariant(self):
        for problem_id, text in [("P003", "-0012\n"), ("P003", "12a3\n"),
                                 ("P004", "-64\n33\n"), ("P005", "-84\n126\n")]:
            layout = Macros()
            PROGRAMS[problem_id](layout)
            rt = Runtime(can_direct_addressing=False)
            with patch("sys.stdin", StringIO(text)), redirect_stdout(StringIO()):
                rt.run(self.ir[problem_id])
            with self.subTest(problem=problem_id, text=text):
                for address, value in rt.memory.items():
                    self.assertTrue(-len(layout.slots) - 2 <= address <= -3 or address == 0 or value == 0,
                                    f"保留范围之外发生非零写入：{address}={value}")

    def test_multiplication_small_signed_square(self):
        for a in range(-16, 17):
            for b in range(-16, 17):
                with self.subTest(a=a, b=b):
                    self.assertEqual(evaluate(self.ir["P004"], f"{a}\n{b}\n"), f"{a * b}\n")

    def test_gcd_small_signed_square(self):
        for a in range(-16, 17):
            for b in range(-16, 17):
                with self.subTest(a=a, b=b):
                    self.assertEqual(evaluate(self.ir["P005"], f"{a}\n{b}\n"), f"{math.gcd(a, b)}\n")

    def test_reproducible_larger_arithmetic(self):
        rng = random.Random(20261106)
        cases = [(0, 0), (-1000, 0), (0, -1000), (-31, -32), (-32, -33), (-33, -34),
                 (42, -100), (-123, -456), (987, 610), (1000, -1)]
        cases += [(rng.randint(-120, 120), rng.randint(-120, 120)) for _ in range(35)]
        for problem_id, oracle in [("P004", lambda a, b: a * b), ("P005", math.gcd)]:
            for a, b in cases:
                with self.subTest(problem=problem_id, a=a, b=b):
                    self.assertEqual(evaluate(self.ir[problem_id], f"{a}\n{b}\n"), f"{oracle(a, b)}\n")

    def test_larger_magnitudes_and_address_collision_boundaries(self):
        cases = [(-64, 3), (64, -7), (-35, -1), (-16, 15), (-17, 16), (-32, -31), (-33, -32)]
        for problem_id, oracle in [("P004", lambda a, b: a * b), ("P005", math.gcd)]:
            for a, b in cases:
                with self.subTest(problem=problem_id, a=a, b=b):
                    self.assertEqual(evaluate(self.ir[problem_id], f"{a}\n{b}\n"), f"{oracle(a, b)}\n")


if __name__ == "__main__":
    unittest.main()
