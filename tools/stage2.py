"""阶段二的纯 PP3 程序构造；字符映射与数组操作均在 DSL 内执行。"""

from tools.arrays import NegativeArray
from tools.macros import compile_program, seq


ERROR_OUTPUT = " ".join(f"&{ord(char)} @print_as_char" for char in "ERROR\n")


def validate_byte(m, char, error):
    """最多走 256 步，判断字符码点是否落在 0..255。"""
    walk, budget, run = (m.slot(name) for name in ("字节探测", "字节预算", "字节探测继续"))
    step = seq(
        m.change(walk, "@-"), m.change(budget, "@-"), m.constant(run, 0),
        m.once(m.read(walk), m.once(m.read(budget), m.constant(run, 1))),
    )
    return seq(
        m.copy(walk, char), m.copy(run, char), m.constant(budget, 256),
        m.loop(m.read(run), step),
        m.if_zero(m.read(budget), m.constant(error, 1)),
    )


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
    mapped, done, remaining = (m.slot(name) for name in ("映射字符", "有限分类完成", "回放剩余"))

    def prepare(m, length):
        return array.reset()

    def consume(m, char):
        def case(index):
            codepoint = 65 + index
            if index < 26:
                codepoint = 65 + (index + 13) % 26
            elif index >= 32:
                codepoint = 97 + (index - 32 + 13) % 26
            return m.constant(mapped, codepoint)

        return seq(
            m.copy(mapped, char), m.constant(done, 0),
            m.read(char) + " " + "@- " * 65,
            m.small_cases("@-", 57, "", case),
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
    counts = NegativeArray(m)
    value, remaining, frequency = (m.slot(name) for name in ("输出字节", "字节桶剩余", "当前频次"))

    def prepare(m, length):
        return ""

    def consume(m, char):
        return seq(counts.seek(char), counts.change("@+"))

    def finish(m, length):
        emit_bucket = seq(
            m.put(frequency, counts.read()),
            m.loop(m.read(frequency), seq(
                m.read(value) + " @print_as_char", m.change(frequency, "@-"),
            )),
            counts.advance(), m.change(value, "@+"), m.change(remaining, "@-"),
        )
        return seq(
            counts.reset(), m.constant(remaining, 256),
            m.loop(m.read(remaining), emit_bucket),
        )

    return frame_program(m, prepare, consume, finish)


def wc(m):
    lines, words, inside, whitespace = (m.slot(name) for name in ("行数", "词数", "词内", "ASCII空白"))

    def prepare(m, length):
        return ""

    def consume(m, char):
        classify = seq(*(m.if_zero(
            m.read(char) + " " + "@- " * value,
            m.constant(whitespace, 1),
        ) for value in (9, 10, 11, 12, 13, 32)))
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
