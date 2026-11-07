"""阶段二的纯 PP3 程序构造；字符映射与数组操作均在 DSL 内执行。"""

from tools.arrays import NegativeArray
from tools.macros import compile_program, seq
from tools.records import RecordHeap, RecordList, merge_sort


ERROR_OUTPUT = " ".join(f"&{ord(char)} @print_as_char" for char in "ERROR\n")


def validate_byte(m, char, error):
    """ord() 已保证非负，只需与最大有效码点做通用比较。"""
    maximum, lt, eq, gt = (m.slot(name) for name in ("最大字节", "字节小于", "字节等于", "字节大于"))
    return seq(m.constant(maximum, 255), m.compare(char, maximum, lt, eq, gt),
               m.once(m.read(gt), m.constant(error, 1)))


def frame_program(m, prepare, consume, finish):
    length, sign, remaining, char, error = (m.slot(name) for name in (
        "帧长", "长度负号", "剩余字符", "帧字符", "帧错误",
    ))
    # 先构造正文以统计槽位，再在运行顺序上放到长度解码之后
    initialize = prepare(m, length)
    process = consume(m, char)
    output = finish(m, length)
    step = seq(
        m.put(char, "@input_as_char"),
        m.if_zero(m.read(error), seq(
            validate_byte(m, char, error),
            m.if_zero(m.read(error), process),
        )),
        m.change(remaining, "@-"),
    )
    valid_length = seq(
        initialize, m.copy(remaining, length),
        m.loop(m.read(remaining), step),
        m.if_nonzero(m.read(error), ERROR_OUTPUT, output),
    )
    return seq(
        m.decode_integer(length, sign),
        m.if_nonzero(m.read(sign), ERROR_OUTPUT, valid_length),
    )


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
