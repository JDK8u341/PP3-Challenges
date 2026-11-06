"""生成纯 PP3 有符号加法程序；Python 只展开静态宏。"""

from pathlib import Path
import argparse
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.runtime import IRBuilder, Runtime, std_register


# 变量数据避开这十个地址，允许保存零
P, Q, K, TMP, RUN, DONE, MAG, SIGN, POS, NEG = range(-1, -11, -1)
BOUND = 11


def seq(*parts):
    return "\n".join(part for part in parts if part)


def read(slot):
    return f"&{slot} ~1"


def select(slot):
    # 即使旧值为零，也能令 memory[0] 指向目标并将目标清零
    return f"&0 ^1 &{slot} ^3 &0 ^2"


def put(slot, expression):
    # 目标在求值前已清零，所以表达式不能读取目标的旧值
    return f"{select(slot)} {expression} ^3"


def literal(slot, value):
    return put(slot, f"&{value}")


def change(slot, op):
    return seq(put(TMP, read(slot)), put(slot, f"{read(TMP)} {op}"))


def once(condition, body):
    return seq(condition, "[", body, "&0", "]")


def small_cases(step, last, fallback, case):
    """用零测试分类逐步偏移的值，DONE 标志用于实现否则分支。"""
    def arm(j):
        nonzero = seq(step, arm(j + 1)) if j < last else fallback
        zero = seq(case(j), literal(DONE, 1))
        return seq(
            "[", nonzero, "&0", "]",
            once(f"{read(DONE)} @-", zero),
        )

    return arm(0)


def decode_input():
    # 输入不在 [-11, 0] 内时，两路搜索都不会进入保留地址范围
    race_step = seq(
        change(P, "@-"),
        change(Q, "@+"),
        change(K, "@+"),
        literal(RUN, 0),
        once(read(P), once(f"{read(Q)} {'@+ ' * BOUND}", literal(RUN, 1))),
        read(RUN),
    )
    classify = seq(
        put(MAG, f"{read(K)} {'@+ ' * BOUND}"),
        literal(SIGN, 1),
        once(
            f"{read(Q)} {'@+ ' * BOUND}",
            seq(put(MAG, read(K)), literal(SIGN, 0)),
        ),
    )
    fallback = seq(
        "@- " * BOUND + "^3",
        put(Q, read(P)), literal(K, 0), literal(RUN, 1),
        read(RUN), "[", race_step, "]",
        classify, literal(DONE, 1),
    )

    def small(j):
        return seq(literal(MAG, j), literal(SIGN, int(j != 0)))

    return seq(
        literal(DONE, 0), select(P), "@input",
        small_cases("@+", BOUND, fallback, small),
    )


def accumulate(slot):
    return seq(read(MAG), "[", change(slot, "@+"), change(MAG, "@-"), read(MAG), "]")


def consume_input():
    return seq(
        decode_input(),
        once(read(SIGN), accumulate(NEG)),
        once(f"{read(SIGN)} @-", accumulate(POS)),
    )


def both_nonzero():
    return seq(
        literal(RUN, 0),
        once(read(POS), once(read(NEG), literal(RUN, 1))),
        read(RUN),
    )


def print_negative():
    # 小负数直接输出立即数；大负数从 -11 开始递减，避开保留地址
    fallback = seq(
        "^3", literal(P, -BOUND), read(K), "[",
        change(P, "@-"), change(K, "@-"), read(K), "]",
        f"{read(P)} @print", literal(DONE, 1),
    )
    return seq(
        literal(DONE, 0), select(K), read(NEG),
        small_cases("@-", BOUND, fallback, lambda j: f"&{-j} @print"),
    )


def make_code():
    cancel = seq(
        both_nonzero(), "[",
        change(POS, "@-"), change(NEG, "@-"), both_nonzero(), "]",
    )
    raw = seq(
        consume_input(), consume_input(), cancel,
        literal(DONE, 0),
        once(read(NEG), print_negative()),
        once(f"{read(DONE)} @-", f"{read(POS)} @print"),
    )
    depth = 0
    lines = []
    for line in raw.splitlines():
        line = line.strip()
        if line == "]":
            depth -= 1
        lines.append("  " * depth + line)
        if line == "[":
            depth += 1
    assert depth == 0
    return "\n".join(lines) + "\n"


code = make_code()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", type=Path, help="写出展开的 PP3 程序后退出")
    args = parser.parse_args()
    if args.export:
        args.export.write_text(code, encoding="ascii")
        return
    builder = IRBuilder(op_map=std_register)
    rt = Runtime(can_direct_addressing=False)
    rt.run(builder.build(code))


if __name__ == "__main__":
    main()
