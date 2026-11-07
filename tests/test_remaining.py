"""剩余四题的独立模型、客体差分和源码往返验证；参考运算仅在测试端。"""

from collections import defaultdict
from contextlib import redirect_stdout
from io import StringIO
import itertools
import random
import unittest
from unittest.mock import patch

from tools.macros import Macros, compile_program, seq
from tools.machines import Arena
from tools.records import Reference
from tools.runtime import ROOT, Runtime, build, problem
from tools.stage3 import PROGRAMS as STAGE3
from tools.stage4 import PROGRAMS as STAGE4
from tools.stage5 import PROGRAMS as STAGE5


PROGRAMS = {**STAGE3, **STAGE4, **STAGE5}


def execute(ir, stdin=""):
    rt, output = Runtime(can_direct_addressing=False), StringIO()
    with patch("sys.stdin", StringIO(stdin)), redirect_stdout(output):
        rt.run(ir)
    return output.getvalue(), rt


def frame(text):
    return f"{len(text)}\n{text}"


def dual(source, data=""):
    return f"{len(source)}\n{len(data)}\n{source}{data}"


def life_input(board, generations, width=None):
    width = len(board[0]) if board else (width or 0)
    return "\n".join(map(str, [len(board), width, generations, *(v for row in board for v in row)])) + "\n"


def reference_life(board, generations):
    height, width = len(board), len(board[0]) if board else 0
    if not height or not width:
        return ""
    for _ in range(generations):
        following = [[0] * width for _ in range(height)]
        for row in range(height):
            for column in range(width):
                neighbors = sum(board[(row + dr) % height][(column + dc) % width]
                                for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr, dc) != (0, 0))
                following[row][column] = int(neighbors == 3 or (board[row][column] and neighbors == 2))
        board = following
    return "".join("".join(map(str, row)) + "\n" for row in board)


def reference_bf(source, data):
    """独立的数组指令、字典带模型；步数限制只保护测试，不约束被测解释器。"""
    code = [char for char in source if char in "><+-.,[]"]
    stack, pairs = [], {}
    for index, char in enumerate(code):
        if char == "[":
            stack.append(index)
        elif char == "]":
            if not stack:
                return "ERROR\n"
            start = stack.pop()
            pairs[start], pairs[index] = index, start
    if stack:
        return "ERROR\n"
    tape, pointer, pc, cursor, steps, output = defaultdict(int), 0, 0, 0, 0, []
    while pc < len(code):
        steps += 1
        if steps > 100000:
            raise AssertionError("测试产生了超出预算的 BF 客体程序")
        char = code[pc]
        if char == ">":
            pointer += 1
        elif char == "<":
            pointer -= 1
        elif char == "+":
            tape[pointer] = (tape[pointer] + 1) % 256
        elif char == "-":
            tape[pointer] = (tape[pointer] - 1) % 256
        elif char == ".":
            output.append(chr(tape[pointer]))
        elif char == ",":
            tape[pointer] = ord(data[cursor]) if cursor < len(data) else 0
            cursor += 1
        elif char == "[" and not tape[pointer]:
            pc = pairs[pc]
        elif char == "]" and tape[pointer]:
            pc = pairs[pc]
        pc += 1
    return "".join(output)


class ArenaTests(unittest.TestCase):
    def test_zero_heads_aliasing_and_independent_fields(self):
        layout = {}

        def program(m):
            heap = Arena(m)
            a, b, c = (m.slot(f"测试.{name}") for name in "ABC")
            layout.update(a=a, b=b, c=c, bump=heap.bump)
            return seq(heap.initialize(), heap.allocate(a), heap.allocate(b),
                       heap.put(a, 1, "&255"), heap.link(a, 4, b), heap.link(b, 4, a),
                       heap.put(b, 1, "&" + str(10**100)), heap.follow(c, a, 4),
                       heap.follow(c, c, 4), heap.allocate(c), Reference.copy(c, a),
                       heap.put(a, 1, "&0"), heap.put(a, 2, "&42"))

        _, rt = execute(build(compile_program(program)))
        a, b, c = (rt.memory[layout[name]] for name in "abc")
        self.assertEqual(c, a)
        self.assertEqual(a - b, 9)
        self.assertEqual(rt.memory[layout["bump"]], a - 27)
        self.assertEqual([rt.memory[a - i] for i in (0, 1, 2, 4)], [0, 0, 42, b])
        self.assertEqual([rt.memory[b - i] for i in (0, 1, 4)], [0, 10**100, a])


class RemainingChallengesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code = {name: compile_program(program) for name, program in PROGRAMS.items()}
        cls.ir = {name: build(code) for name, code in cls.code.items()}
        cls.layout = Macros()
        PROGRAMS["P012"](cls.layout)

    def test_standard_operations_and_reproducible_sources(self):
        for name, code in self.code.items():
            with self.subTest(problem=name):
                self.assertEqual(code, compile_program(PROGRAMS[name]))
                self.assertEqual(code, (ROOT / problem(name)["directory"] / "solution.pp3").read_text(encoding="ascii"))
                self.assertLessEqual({part for part in code.split() if part.startswith("@")},
                                     {"@input", "@input_as_char", "@print_as_char", "@+", "@-"})

    def test_life_known_patterns_and_wrapping(self):
        patterns = [[], [[], []], [[0]], [[1]], [[1, 0]], [[1], [0]],
                    [[0]*5, [0, 1, 1, 0, 0], [0, 1, 1, 0, 0], [0]*5, [0]*5],
                    [[0]*5, [0]*5, [0, 1, 1, 1, 0], [0]*5, [0]*5],
                    [[1, 0, 0, 0, 1], [1, 0, 0, 0, 0], [0]*5, [0]*5, [0, 0, 0, 1, 1]]]
        for board in patterns:
            for generation in (0, 1, 2, 4):
                with self.subTest(board=board, generation=generation):
                    output, _ = execute(self.ir["P009"], life_input(board, generation))
                    self.assertEqual(output, reference_life(board, generation))

    def test_life_all_small_tori(self):
        for height, width in ((1, 1), (1, 2), (2, 1), (2, 2)):
            for values in itertools.product((0, 1), repeat=height * width):
                board = [list(values[row * width:(row + 1) * width]) for row in range(height)]
                output, _ = execute(self.ir["P009"], life_input(board, 2))
                self.assertEqual(output, reference_life(board, 2))

    def test_life_random_rectangles(self):
        rng = random.Random(9009)
        for _ in range(16):
            height, width, generations = rng.randrange(1, 6), rng.randrange(1, 6), rng.randrange(5)
            board = [[rng.randrange(2) for _ in range(width)] for _ in range(height)]
            output, _ = execute(self.ir["P009"], life_input(board, generations))
            self.assertEqual(output, reference_life(board, generations))

    def test_life_errors_and_zero_dimensions(self):
        for stdin in ("-1\n2\n0\n", "2\n-1\n0\n", "2\n2\n-1\n",
                      "1\n3\n1\n1\n2\n0\n", "1\n2\n0\n-1\n0\n"):
            with self.subTest(stdin=stdin):
                self.assertEqual(execute(self.ir["P009"], stdin)[0], "ERROR\n")
        for stdin in ("0\n7\n2\n", "3\n0\n100\n", "0\n0\n0\n"):
            self.assertEqual(execute(self.ir["P009"], stdin)[0], "")

    def test_text_generator_roundtrip_all_bytes_and_special_characters(self):
        texts = ["", "\x00", "\n", "\"'\\[]&@", "Hello\nPP3!", "".join(map(chr, range(256)))]
        rng = random.Random(1010)
        texts += ["".join(chr(rng.randrange(256)) for _ in range(rng.randrange(25))) for _ in range(8)]
        for text in texts:
            with self.subTest(text=ascii(text)):
                generated, _ = execute(self.ir["P010"], frame(text))
                self.assertEqual(execute(build(generated))[0], text)
                self.assertEqual(generated, "".join(f"&{ord(char)} @print_as_char\n" for char in text))

    def check_bf(self, source, data=""):
        output, rt = execute(self.ir["P011"], dual(source, data))
        self.assertEqual(output, reference_bf(source, data))
        return rt

    def test_bf_eight_operations_wrap_comments_and_nesting(self):
        for code, data in [("", ""), ("comments", ""), ("-.", ""), ("-+.", ""),
                           ("+"*256 + ".", ""), ("<+>++.<.", ""), ("[-][][[]].", ""),
                           ("++[>++[>+++<-]<-]>>.", ""), (",.,.,.", "\x00\xff"),
                           ("+,[.-]", ""), (",.,.", "A"), ("[,].", "\xff\x00")]:
            with self.subTest(code=code):
                self.check_bf(code, data)

    def test_bf_linked_tape_reverses_framed_text(self):
        # 本测试现场构造的短程序：向右读至零，向左逐格倒序输出。
        for text in ("", "PP3", "A\nB", "\xffZ!"):
            source = ",[>,]<[.<]"
            self.assertEqual(execute(self.ir["P011"], dual(source, text))[0], text[::-1])

    def test_bf_hello_world_integration(self):
        source = ("++++++++++[>+++++++>++++++++++>+++>+<<<<-]>++.>+.+++++++..+++."
                  ">++.<<+++++++++++++++.>.+++.------.--------.>+.>.")
        output, _ = execute(self.ir["P011"], dual(source))
        self.assertEqual(output, "Hello World!\n")
        self.assertEqual(output, reference_bf(source, ""))

    def test_bf_reproducible_random_terminating_programs(self):
        rng = random.Random(1111)
        fragments = ["+", "-", ">", "<", ".", ",", "[-]", "++[>+++<-]", "[-][]", "[>]", "\x00comment"]
        for _ in range(20):
            source = "".join(rng.choice(fragments) for _ in range(12))
            data = "".join(chr(rng.randrange(256)) for _ in range(8))
            with self.subTest(source=source):
                self.check_bf(source, data)

    def test_bf_rejects_all_unbalanced_brackets_before_output(self):
        for source in ("[", "]", ".[", ".]", "[[[]]", "][", "[]]"):
            self.assertEqual(execute(self.ir["P011"], dual(source))[0], "ERROR\n")

    def check_pp3(self, source, data=""):
        expected, original = execute(build(source), data)
        actual, interpreter = execute(self.ir["P012"], dual(source, data))
        self.assertEqual(actual, expected)
        slots, store = self.layout.slots, interpreter.memory
        magnitude, sign = store[slots["自解释.view幅值"]], store[slots["自解释.view负号"]]
        self.assertIn(sign, (0, 1))
        if not magnitude:
            self.assertEqual(sign, 0)
        self.assertEqual(magnitude * (-1 if sign else 1), original.view)
        cursor, observed, visited = store[slots["客体内存.表头"]], {}, set()
        while cursor:
            self.assertNotIn(cursor, visited)
            visited.add(cursor)
            key = store[cursor - 1] * (-1 if store[cursor - 2] else 1)
            value = store[cursor - 3] * (-1 if store[cursor - 4] else 1)
            for magnitude_field, sign_field in ((1, 2), (3, 4)):
                self.assertIn(store[cursor - sign_field], (0, 1))
                if not store[cursor - magnitude_field]:
                    self.assertEqual(store[cursor - sign_field], 0)
            self.assertNotIn(key, observed)
            observed[key] = value
            cursor = store[cursor - 8]
        self.assertEqual(list(observed.items()), list(original.memory.items()))
        return interpreter

    def test_pp3_signed_values_zero_crossings_and_character_modulo(self):
        for source in ("", "&-0 @print_as_char", "&+001 @- @- @+ @print_as_char",
                       "&-257 @print_as_char @+ @print_as_char @+ @print_as_char",
                       "&-1 @+ @+ @- @- @print_as_char", "&512 @print_as_char"):
            with self.subTest(source=source):
                self.check_pp3(source)

    def test_pp3_graph_routes_swaps_cycles_and_signed_keys(self):
        samples = ["&0 ^1 &0 ~1 *1", "&-7 ^1 &-7 ~3 *2 ^4",
                   "&7 ^1 &7 ~5 *3 &0 ^2 &0 ~3", "&-4 ^1 &3 ^2 &-4 *2 ~1",
                   "&65 ^2 &0 ~1 @print_as_char &0 *1 @print_as_char",
                   "&-2 ^1 &-2 *1 &-2 ~1 ^2 &0 ~2"]
        rng = random.Random(1212)
        for _ in range(20):
            parts = []
            for _ in range(12):
                parts.append(rng.choice((f"&{rng.randrange(-12,13)}", f"~{rng.randrange(1,5)}",
                                         f"^{rng.randrange(1,5)}", f"*{rng.randrange(1,5)}", "@+", "@-")))
            samples.append(" ".join(parts))
        for source in samples:
            with self.subTest(source=source):
                self.check_pp3(source)

    def test_pp3_nested_empty_skipped_and_negative_loops(self):
        for source in ("&0 [ ]", "&3 [ @- ]", "&-3 [ @+ ]", "&0 [ @input_as_char ]",
                       "&0 [ &9 [ ] ] &65 @print_as_char",
                       "&2 [ @- [ @- ] ]"):
            with self.subTest(source=source):
                self.check_pp3(source)

    def test_pp3_ascii_whitespace_positive_depth_spelling_and_io(self):
        self.check_pp3("\t&+0065\r\n^+01\v&65\f~001 @print_as_char ")
        for data in ("A", "\x00", "\xff", "\n"):
            self.check_pp3("@input_as_char ^1 @print_as_char @+ @print_as_char", data)

    def test_pp3_rejects_unsupported_and_invalid_tokens_before_execution(self):
        invalid = ("@input", "@print", "@debug", "#1", "$1", "%1", "&", "&+", "&--1", "&1_0", "&1x",
                   "~0", "~+0", "~-1", "^0", "*0", "~", "@unknown", "[]", "[x", "]", "[", "[ ] ]",
                   "&1\xa0@+", "&1@+", "&1.0")
        for token in invalid:
            with self.subTest(token=token):
                source = "&65 @print_as_char " + token
                self.assertEqual(execute(self.ir["P012"], dual(source))[0], "ERROR\n")

    def test_pp3_guest_eof_keeps_prior_output_and_stops(self):
        source = "&65 @print_as_char @input_as_char @print_as_char"
        self.assertEqual(execute(self.ir["P012"], dual(source))[0], "AERROR\n")
        self.assertEqual(execute(self.ir["P012"], dual(source, "Z"))[0], "AZ")

    def test_generated_source_also_executes_in_pp3_subset_interpreter(self):
        text = "P\x00\xff\n"
        generated, _ = execute(self.ir["P010"], frame(text))
        self.assertEqual(execute(self.ir["P012"], dual(generated))[0], text)

    def test_new_character_programs_validate_frames_before_output(self):
        for name in ("P010", "P011", "P012"):
            inputs = ["-1\n"] if name == "P010" else ["-1\n0\n", "0\n-1\n", "-300\n1\n"]
            inputs += [frame("A中B")] if name == "P010" else [dual(".", "中"), dual("中", "")]
            for stdin in inputs:
                with self.subTest(problem=name, stdin=stdin):
                    self.assertEqual(execute(self.ir[name], stdin)[0], "ERROR\n")

    def test_dual_frames_consume_all_payload_even_after_source_error(self):
        for name, source in (("P011", "]"), ("P012", "@unknown")):
            output, rt = execute(self.ir[name], dual(source, "AB") + "tail\n")
            self.assertEqual(output, "ERROR\n")
            self.assertEqual("".join(rt.std_register["input_as_char"].buffer), "tail\n")

    def test_dual_frames_zero_lengths_and_integer_header_spelling(self):
        for name in ("P011", "P012"):
            output, rt = execute(self.ir[name], "-0\n +0000 \n")
            self.assertEqual(output, "")
            self.assertEqual(list(rt.std_register["input_as_char"].buffer), [])
            output, rt = execute(self.ir[name], "0\n2\nABtail\n")
            self.assertEqual(output, "")
            self.assertEqual("".join(rt.std_register["input_as_char"].buffer), "tail\n")

    def test_dual_frame_boundary_and_synthetic_lf(self):
        source = "@input_as_char @print_as_char"
        self.assertEqual(execute(self.ir["P012"], dual(source, "\n"))[0], "\n")
        # 实际文本在源码末尾结束；字符处理器补回的 LF 属于数据帧。
        self.assertEqual(execute(self.ir["P012"], f"{len(source)}\n1\n{source}")[0], "\n")
        output, rt = execute(self.ir["P011"], dual("+.") + "中\n")
        self.assertEqual(output, "\x01")
        self.assertEqual("".join(rt.std_register["input_as_char"].buffer), "中\n")

    def test_guest_input_cannot_consume_beyond_data_frame(self):
        for name, source, expected in (("P011", ",.,.", "Z\x00"),
                                       ("P012", "@input_as_char @print_as_char @input_as_char @print_as_char", "ZERROR\n")):
            output, rt = execute(self.ir[name], dual(source, "Z") + "outside\n")
            self.assertEqual(output, expected)
            self.assertEqual("".join(rt.std_register["input_as_char"].buffer), "outside\n")

    def test_all_machine_records_preserve_permanent_zero_heads(self):
        for name, stdin in (("P009", life_input([[1, 0], [0, 1]], 3)),
                            ("P011", dual("++[>+<-]<+>.<.")),
                            ("P012", dual("&-7 ^2 &0 ~1 *2 @print_as_char"))):
            layout = Macros()
            PROGRAMS[name](layout)
            _, rt = execute(self.ir[name], stdin)
            base, bump = -len(layout.slots) - 3, rt.memory[layout.slots["机器堆.未使用地址"]]
            self.assertEqual((base - bump) % 9, 0)
            for head in range(base, bump, -9):
                self.assertEqual(rt.memory[head], 0, f"{name} 覆盖了永久零头")
            self.assertTrue(all(value == 0 for address, value in rt.memory.items() if address > 0))

    def test_frame_early_eof_and_integer_header_errors(self):
        for name in ("P009", "P010", "P011", "P012"):
            for stdin, exception in [("", EOFError), ("bad\n", ValueError)]:
                with self.subTest(problem=name, stdin=stdin):
                    output = StringIO()
                    with patch("sys.stdin", StringIO(stdin)), redirect_stdout(output), self.assertRaises(exception):
                        Runtime(can_direct_addressing=False).run(self.ir[name])
                    self.assertEqual(output.getvalue(), "")
        for name, stdin in (("P009", "1\n1\n0\n"), ("P010", "4\nAB"),
                            ("P011", "1\n3\n.A"), ("P012", "1\n3\n]A")):
            with self.subTest(problem=name):
                output = StringIO()
                with patch("sys.stdin", StringIO(stdin)), redirect_stdout(output), self.assertRaises(EOFError):
                    Runtime(can_direct_addressing=False).run(self.ir[name])
                self.assertEqual(output.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
