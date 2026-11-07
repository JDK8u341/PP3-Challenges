"""阶段二的纯 PP3 程序构造；字符映射与数组操作均在 DSL 内执行。"""

from pp3_toolkit import NegativeArray, RecordHeap, RecordList, compile_program, merge_sort, seq
from pp3_toolkit.frames import ERROR_OUTPUT, frame_program


def rot13(m):
    array = NegativeArray(m)
    mapped, remaining, upper, lower, start, offset, half, lt, eq, gt = (m.slot(name) for name in (
        "映射字符", "回放剩余", "大写字母", "小写字母", "字母起点", "字母偏移", "半字母表",
        "旋转小于", "旋转等于", "旋转大于"))

    def prepare(m, length):
        return array.reset()

    def consume(m, char):
        rotate = seq(
            m.copy(offset, char), m.subtract_from(offset, start), m.constant(half, 13),
            m.compare(offset, half, lt, eq, gt),
            m.if_nonzero(m.read(lt), m.put(mapped, m.read(char) + " " + "@+ " * 13),
                         m.put(mapped, m.read(char) + " " + "@- " * 13)),
        )
        return seq(
            m.copy(mapped, char), m.in_range(char, 65, 90, upper), m.in_range(char, 97, 122, lower),
            m.if_nonzero(m.read(upper), seq(m.constant(start, 65), rotate),
                         m.once(m.read(lower), seq(m.constant(start, 97), rotate))),
            array.put(m.read(mapped)), array.advance(),
        )

    def finish(m, length):
        return seq(
            array.reset(), m.copy(remaining, length),
            m.loop(m.read(remaining), seq(
                array.read() + " @print_as_char", array.advance(), m.change(remaining, "@-"),
            )),
        )

    return frame_program(m, prepare, consume, finish)


def byte_sort(m):
    heap = RecordHeap(m)
    data = RecordList(heap, "排序数据")
    node, sign = m.slot("排序节点"), m.slot("排序零符号")

    def prepare(m, length):
        return heap.initialize()

    def consume(m, char):
        return seq(heap.allocate(node, char, sign), data.append(node))

    def finish(m, length):
        return seq(merge_sort(m, data, length), m.loop(m.read(data.head), seq(
            data.pop(node), heap.read(node, RecordHeap.MAGNITUDE) + " @print_as_char",
        )))

    return frame_program(m, prepare, consume, finish)


def wc(m):
    lines, words, inside, whitespace = (m.slot(name) for name in ("行数", "词数", "词内", "ASCII空白"))

    def prepare(m, length):
        return ""

    def consume(m, char):
        classify = seq(m.in_range(char, 9, 13, whitespace),
                       m.if_zero(m.read(char) + " " + "@- " * 32, m.constant(whitespace, 1)))
        return seq(
            m.if_zero(m.read(char) + " " + "@- " * 10, m.change(lines, "@+")),
            m.constant(whitespace, 0), classify,
            m.if_nonzero(m.read(whitespace), m.constant(inside, 0), seq(
                m.if_zero(m.read(inside), m.change(words, "@+")), m.constant(inside, 1),
            )),
        )

    def finish(m, length):
        return seq(
            m.print_unsigned_decimal(lines), "&32 @print_as_char",
            m.print_unsigned_decimal(words), "&32 @print_as_char",
            m.print_unsigned_decimal(length), "&10 @print_as_char",
        )

    return frame_program(m, prepare, consume, finish)


PROGRAMS = {"P006": rot13, "P007": byte_sort, "P008": wc}


def make_code(problem_id):
    return compile_program(PROGRAMS[problem_id])
