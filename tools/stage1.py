"""阶段一三题的编译期程序构造；所有解题运算由生成的 PP3 完成。"""

from tools.macros import compile_program, seq


def decimal_codec(m):
    char, digit, magnitude, sign, first, seen, error, run = (m.slot(name) for name in (
        "当前字符", "当前数字", "整数幅值", "负号", "首字符", "见过数字", "错误", "继续输入",
    ))
    invalid, done = m.slot("非法数字"), m.slot("有限分类完成")
    decode_digit = seq(
        m.constant(invalid, 0), m.constant(done, 0),
        m.read(char) + " " + "@- " * 48,
        m.small_cases("@-", 9, m.constant(invalid, 1), lambda index: m.constant(digit, index)),
        m.if_nonzero(m.read(invalid), m.constant(error, 1), seq(
            m.multiply_by_ten(magnitude), m.add_into(magnitude, digit), m.constant(seen, 1),
        )),
    )
    sign_or_digit = m.if_nonzero(
        m.read(char) + " " + "@- " * 43,
        m.if_nonzero(m.read(char) + " " + "@- " * 45, decode_digit, m.constant(sign, 1)),
    )
    character_step = seq(
        m.put(char, "@input_as_char"),
        m.if_nonzero(m.read(char) + " " + "@- " * 10,
            m.if_nonzero(m.read(error), "", m.if_nonzero(m.read(first), seq(
                m.constant(first, 0), sign_or_digit,
            ), decode_digit)),
            m.constant(run, 0),
        ),
    )
    normal_output = seq(
        m.once(m.read(magnitude), m.once(m.read(sign), "&45 @print_as_char")),
        m.print_unsigned_decimal(magnitude), "&10 @print_as_char",
    )
    error_output = " ".join(f"&{ord(char)} @print_as_char" for char in "ERROR\n")
    return seq(
        m.constant(first, 1), m.constant(run, 1),
        m.loop(m.read(run), character_step),
        m.if_zero(m.read(seen), m.constant(error, 1)),
        m.if_nonzero(m.read(error), error_output, normal_output),
    )


def signed_multiply(m):
    a, b, sa, sb, product, counter = (m.slot(name) for name in (
        "A幅值", "B幅值", "A负号", "B负号", "乘积", "乘法计数",
    ))
    return seq(
        m.decode_integer(a, sa), m.decode_integer(b, sb),
        m.copy(counter, b),
        m.loop(m.read(counter), seq(m.add_into(product, a), m.change(counter, "@-"))),
        m.once(m.read(product), m.if_nonzero(
            m.read(sa), m.if_zero(m.read(sb), "&45 @print_as_char"),
            m.once(m.read(sb), "&45 @print_as_char"),
        )),
        m.read(product) + " @print",
    )


def gcd(m):
    a, b, sign, q, r = (m.slot(name) for name in ("A幅值", "B幅值", "忽略符号", "余除商", "余除余数"))
    return seq(
        m.decode_integer(a, sign), m.decode_integer(b, sign),
        m.loop(m.read(b), seq(m.divmod_unsigned(a, b, q, r), m.copy(a, b), m.copy(b, r))),
        m.read(a) + " @print",
    )


PROGRAMS = {"P003": decimal_codec, "P004": signed_multiply, "P005": gcd}


def make_code(problem_id):
    return compile_program(PROGRAMS[problem_id])
