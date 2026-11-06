"""阶段一的静态宏：只生成 PP3 文本，不读取或计算题目输入。"""


def seq(*parts):
    return "\n".join(part for part in parts if part)


def format_code(code):
    depth = 0
    lines = []
    for line in code.splitlines():
        line = line.strip()
        if not line:
            continue
        if line == "]":
            depth -= 1
        if depth < 0:
            raise ValueError("生成的循环括号不匹配")
        lines.append("  " * depth + line)
        if line == "[":
            depth += 1
    if depth:
        raise ValueError("生成的循环括号未闭合")
    return "\n".join(lines) + "\n"


class Macros:
    def __init__(self, bound=1):
        self.bound = bound
        self.slots = {}
        self.flag_count = 0

    def slot(self, name):
        if name not in self.slots:
            self.slots[name] = -len(self.slots) - 1
        return self.slots[name]

    def flag(self):
        self.flag_count += 1
        return self.slot(f"条件标志{self.flag_count}")

    @staticmethod
    def read(slot):
        return f"&{slot} ~1"

    @staticmethod
    def select(slot):
        return f"&0 ^1 &{slot} ^3 &0 ^2"

    def put(self, slot, expression):
        return f"{self.select(slot)} {expression} ^3"

    def constant(self, slot, value):
        return self.put(slot, f"&{value}")

    def copy(self, destination, source):
        return "" if destination == source else self.put(destination, self.read(source))

    @staticmethod
    def change(slot, operation):
        # 先取出旧值并恢复目标自环，零值写回时也能沿两次跳转回到目标
        if operation not in ("@+", "@-"):
            raise ValueError("更新宏只接受自增或自减")
        return f"&0 ^1 &{slot} ^3 &{slot} *1 {operation} ^3"

    @staticmethod
    def once(condition, body):
        return seq(condition, "[", body, "&0", "]")

    def if_nonzero(self, condition, nonzero, zero=""):
        flag = self.flag()
        return seq(
            self.constant(flag, 1),
            self.once(condition, seq(self.constant(flag, 0), nonzero)),
            self.once(self.read(flag), zero),
        )

    def if_zero(self, condition, body):
        return self.if_nonzero(condition, "", body)

    @staticmethod
    def loop(condition, body):
        return seq(condition, "[", body, condition, "]")

    def small_cases(self, step, last, fallback, case):
        done = self.slot("有限分类完成")

        def arm(index):
            nonzero = seq(step, arm(index + 1)) if index < last else seq(fallback, self.constant(done, 1))
            return seq(
                "[", nonzero, "&0", "]",
                self.once(f"{self.read(done)} @-", seq(case(index), self.constant(done, 1))),
            )

        return arm(0)

    def decode_integer(self, magnitude, sign):
        """读取一行整数，输出非负幅值和负号标志，不保留危险地址载荷。"""
        p, q, k, run = (self.slot(name) for name in ("解码P", "解码Q", "解码步数", "解码继续"))
        done = self.slot("有限分类完成")
        q_test = f"{self.read(q)} " + "@+ " * self.bound
        step = seq(
            self.change(p, "@-"), self.change(q, "@+"), self.change(k, "@+"),
            self.constant(run, 0),
            self.once(self.read(p), self.once(q_test, self.constant(run, 1))),
        )
        classify = seq(
            self.put(magnitude, f"{self.read(k)} " + "@+ " * self.bound),
            self.constant(sign, 1),
            self.once(q_test, seq(self.copy(magnitude, k), self.constant(sign, 0))),
        )
        fallback = seq(
            "@- " * self.bound + "^3",
            self.copy(q, p), self.constant(k, 0), self.constant(run, 1),
            self.loop(self.read(run), step), classify,
        )
        cases = self.small_cases(
            "@+", self.bound, fallback,
            lambda index: seq(self.constant(magnitude, index), self.constant(sign, int(index != 0))),
        )
        return seq(self.constant(done, 0), self.select(p), "@input", cases)

    def add_into(self, destination, source):
        counter = self.slot("加法计数")
        if counter in (destination, source):
            raise ValueError("加法参数不能使用内部计数槽")
        return seq(
            self.copy(counter, source),
            self.loop(self.read(counter), seq(self.change(destination, "@+"), self.change(counter, "@-"))),
        )

    def multiply_by_ten(self, value):
        counter = self.slot("乘十计数")
        return seq(
            self.copy(counter, value), self.constant(value, 0),
            self.loop(self.read(counter), seq(
                *(self.change(value, "@+") for _ in range(10)),
                self.change(counter, "@-"),
            )),
        )

    def divmod_unsigned(self, numerator, denominator, quotient, remainder):
        """要求非负分子、正分母，结果槽与内部工作槽互异。"""
        work, divisor, countdown = (self.slot(name) for name in ("除法工作", "除法分母", "除法倒数"))
        if {work, divisor, countdown} & {numerator, denominator, quotient, remainder}:
            raise ValueError("除法参数不能使用内部工作槽")
        if quotient == remainder:
            raise ValueError("商和余数必须使用不同槽位")
        step = seq(
            self.change(work, "@-"), self.change(remainder, "@+"), self.change(countdown, "@-"),
            self.if_zero(self.read(countdown), seq(
                self.constant(remainder, 0), self.change(quotient, "@+"), self.copy(countdown, divisor),
            )),
        )
        return seq(
            self.copy(work, numerator), self.copy(divisor, denominator), self.copy(countdown, divisor),
            self.constant(quotient, 0), self.constant(remainder, 0),
            self.loop(self.read(work), step),
        )

    def print_unsigned_decimal(self, value):
        """逐位用字符操作输出非负整数，不调用整数 @print。"""
        number, scale, probe, ten, q, r = (self.slot(name) for name in (
            "输出数值", "输出位权", "输出探测", "常数十", "输出商", "输出余数",
        ))
        scale_step = seq(
            self.divmod_unsigned(probe, ten, q, r), self.copy(probe, q),
            self.once(self.read(probe), self.multiply_by_ten(scale)),
        )
        digit_step = seq(
            self.divmod_unsigned(number, scale, q, r),
            self.read(q) + " " + "@+ " * 48 + "@print_as_char",
            self.copy(number, r),
            self.divmod_unsigned(scale, ten, q, r), self.copy(scale, q),
        )
        return seq(
            self.copy(number, value), self.copy(probe, value), self.constant(scale, 1), self.constant(ten, 10),
            self.loop(self.read(probe), scale_step), self.loop(self.read(scale), digit_step),
        )


def compile_program(program):
    # 首遍只统计固定槽位；第二遍再把负侧安全边界展开为具体常量
    preview = Macros()
    program(preview)
    macros = Macros(bound=len(preview.slots) + 1)
    code = program(macros)
    if macros.slots != preview.slots:
        raise ValueError("两遍生成的槽位布局不同")
    return format_code(code)
