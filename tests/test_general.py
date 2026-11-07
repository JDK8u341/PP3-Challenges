"""通用链表排序、区间判断和布局约束；参考运算仅存在于测试端。"""

from contextlib import redirect_stdout
from io import StringIO
import itertools
import random
import unittest
from unittest.mock import patch

from pp3_toolkit import Macros, RecordHeap, RecordList, compile_program, merge_sort, seq
from tools.runtime import Runtime, build


class GeneralAlgorithmsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        def program(m):
            heap = RecordHeap(m)
            data = RecordList(heap, "测试排序")
            count, remaining, value, index, node = (m.slot(name) for name in (
                "测试数量", "测试剩余", "测试载荷", "原始序号", "测试节点"))
            return seq(
                heap.initialize(), m.put(count, "@input"), m.copy(remaining, count),
                m.loop(m.read(remaining), seq(
                    m.put(value, "@input"), heap.allocate(node, value, index), data.append(node),
                    m.change(index, "@+"), m.change(remaining, "@-"),
                )), merge_sort(m, data, count),
            )

        cls.layout = Macros()
        program(cls.layout)
        cls.base = -len(cls.layout.slots) - 3
        cls.code = compile_program(program)
        cls.ir = build(cls.code)

    def check_sort(self, values):
        rt = Runtime(can_direct_addressing=False)
        stdin = "\n".join(map(str, [len(values), *values])) + "\n"
        with patch("sys.stdin", StringIO(stdin)), redirect_stdout(StringIO()):
            rt.run(self.ir)
        head = self.layout.slots["测试排序.表头"]
        tail = self.layout.slots["测试排序.表尾"]
        cursor = rt.memory[head]
        observed, visited = [], set()
        while cursor:
            self.assertNotIn(cursor, visited, "排序产生环或重复所有权")
            visited.add(cursor)
            self.assertEqual(rt.memory[cursor], 0, "永久零头被覆盖")
            observed.append((rt.memory[cursor - 1], rt.memory[cursor - 2]))
            successor = rt.memory[cursor - 3]
            if not successor:
                self.assertEqual(rt.memory[tail], cursor)
            cursor = successor
        self.assertEqual(observed, sorted((value, index) for index, value in enumerate(values)))
        self.assertEqual(visited, {self.base - 4 * index for index in range(len(values))})
        if not values:
            self.assertEqual(rt.memory[tail], 0)
        for name, slot in self.layout.slots.items():
            if name.endswith((".表头", ".表尾")) and not name.startswith("测试排序."):
                self.assertEqual(rt.memory[slot], 0, "临时链表未转移全部所有权")
        self.assertEqual((rt.memory[-1], rt.memory[-2]), (0, 0))
        self.assertTrue(all(value == 0 for address, value in rt.memory.items() if address > 0))

    def test_stability_and_ownership_for_all_short_ternary_sequences(self):
        for length in range(5):
            for values in itertools.product((0, 1, 2), repeat=length):
                with self.subTest(values=values):
                    self.check_sort(values)

    def test_non_byte_payloads_and_irregular_run_lengths(self):
        samples = [[], [10**100], [10**100] * 7, [10**100, 0, 17, 1, 10**100],
                   [1001, 0, 256, 300, 256, 17, 999],
                   [4096, 1, 4096, 0, 257], list(reversed(range(17))), list(range(17))]
        rng = random.Random(707)
        samples += [[rng.randrange(700) for _ in range(length)] for length in (3, 5, 9, 15, 17, 31)]
        for values in samples:
            with self.subTest(values=values):
                self.check_sort(values)

    def test_unsigned_storage_rejects_raw_negative_constants(self):
        m = Macros()
        with self.assertRaises(ValueError):
            m.constant(m.slot("数据"), -1)

    def test_arbitrary_range_uses_fixed_comparison_code(self):
        def program(m):
            value, result = m.slot("值"), m.slot("区间结果")
            return seq(m.put(value, "@input"), m.in_range(value, 123, 1000, result), m.read(result) + " @print")

        ir = build(compile_program(program))
        for value in (0, 122, 123, 124, 999, 1000, 1001, 10000):
            with patch("sys.stdin", StringIO(f"{value}\n")), redirect_stdout(StringIO()) as output:
                Runtime(can_direct_addressing=False).run(ir)
            self.assertEqual(output.getvalue(), f"{int(123 <= value <= 1000)}\n")


if __name__ == "__main__":
    unittest.main()
