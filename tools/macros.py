"""基于零锚点和局部路由的静态宏；生成器不接收题目输入。"""


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
    SET_MARK = -1
    EQUAL_MARK = -2

    def __init__(self, bound=3):
        self.bound = bound
        self.slots = {}
        self.flag_count = 0

    def slot(self, name):
        if name not in self.slots:
            self.slots[name] = -len(self.slots) - 3
        return self.slots[name]

    @property
    def array_base(self):
        return -self.bound

    def flag(self):
        self.flag_count += 1
        return self.slot(f"条件标志{self.flag_count}")

    @staticmethod
    def read(slot):
        return f"&{slot} ~1"

    @staticmethod
    def select(slot):
        return f"&0 ^1 &{slot} ^4 &{slot} ^1"

    def put(self, slot, expression):
        return f"{self.select(slot)} {expression} ^4"

    def constant(self, slot, value):
        if value < 0:
            raise ValueError("普通数据槽只接受非负常量")
        return self.put(slot, f"&{value}")

    def copy(self, destination, source):
        return "" if destination == source else self.put(destination, self.read(source))

    @staticmethod
    def change(slot, operation):
        # 交换保留旧值；自环补齐经标记或零值返回目标的路径。
        if operation not in ("@+", "@-"):
            raise ValueError("更新宏只接受自增或自减")
        return f"&0 ^1 &{slot} ^4 &{slot} *1 {operation} ^4"

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

    def conjunction(self, left, right, result):
        if result in (left, right):
            raise ValueError("合取输出不得覆盖输入")
        return seq(self.constant(result, 0), self.once(self.read(left),
                   self.once(self.read(right), self.constant(result, 1))))

    def write_marker(self, pointer, marker):
        if marker not in (0, self.SET_MARK, self.EQUAL_MARK):
            raise ValueError("正地址只接受零锚点标记")
        return f"&0 ^1 {self.read(pointer)} ^3 {self.read(pointer)} ^1 &{marker} ^4 &0 ^1"

    def equal(self, left, right, result):
        """借自然数加一后的地址判等，退出时恢复原标记。"""
        pointer, saved = self.slot("等值地址"), self.slot("等值原标记")
        if result in (left, right, pointer, saved) or {left, right} & {pointer, saved}:
            raise ValueError("等值参数不能覆盖输入或内部槽")
        return seq(
            self.put(pointer, self.read(left) + " @+"),
            self.constant(saved, 0), self.constant(result, 0),
            self.once(self.read(pointer) + " ~1", self.constant(saved, 1)),
            self.write_marker(pointer, self.EQUAL_MARK),
            self.if_zero(self.read(right) + " @+ ~1 @+ @+", self.constant(result, 1)),
            self.if_nonzero(self.read(saved), self.write_marker(pointer, self.SET_MARK),
                            self.write_marker(pointer, 0)),
        )

    def compare(self, left, right, lt, eq, gt):
        """自然数比较保留输入；相等先判定，否则同步递减副本。"""
        if len({lt, eq, gt}) != 3 or {lt, eq, gt} & {left, right}:
            raise ValueError("比较输出必须互异且不能覆盖输入")
        a, b, run = (self.slot(name) for name in ("比较副本A", "比较副本B", "比较继续"))
        if {a, b, run} & {left, right, lt, eq, gt}:
            raise ValueError("比较参数不能使用内部槽")
        race = seq(
            self.copy(a, left), self.copy(b, right), self.conjunction(a, b, run),
            self.loop(self.read(run), seq(self.change(a, "@-"), self.change(b, "@-"),
                                         self.conjunction(a, b, run))),
            self.if_nonzero(self.read(a), self.constant(gt, 1), self.constant(lt, 1)),
        )
        return seq(self.constant(lt, 0), self.constant(gt, 0), self.equal(left, right, eq),
                   self.if_zero(self.read(eq), race))

    def in_range(self, value, low, high, result):
        """闭区间判断使用两次通用比较，不展开区间内的值。"""
        lower, upper, lt, eq, gt = (self.slot(name) for name in (
            "区间下界", "区间上界", "区间小于", "区间等于", "区间大于"))
        if result == value or {value, result} & {lower, upper, lt, eq, gt}:
            raise ValueError("区间输入输出不得重叠或使用内部槽")
        if not 0 <= low <= high:
            raise ValueError("自然数区间要求 0<=下界<=上界")
        return seq(
            self.constant(lower, low), self.constant(upper, high), self.constant(result, 0),
            self.compare(value, lower, lt, eq, gt),
            self.if_zero(self.read(lt), seq(self.compare(value, upper, lt, eq, gt),
                         self.if_zero(self.read(gt), self.constant(result, 1)))),
        )

    def decode_integer(self, magnitude, sign):
        """双向探测裸整数；只保护两个原始值槽，不枚举保留地址区间。"""
        p, q, k, run = (self.slot(name) for name in ("解码P", "解码Q", "解码步数", "解码继续"))
        if len({magnitude, sign, p, q, k, run}) != 6:
            raise ValueError("解码结果不得覆盖内部槽或彼此覆盖")

        def select_raw(slot):
            return f"&0 ^1 &{slot} ^5 &{slot} ^1"

        def put_raw(slot, expression):
            return f"{select_raw(slot)} {expression} ^5"

        def finish(expression, negative):
            return seq(self.put(magnitude, expression), self.constant(sign, negative), self.constant(run, 0))

        def advance(slot, operation):
            probe = self.read(slot) + " " + operation
            guards = []
            for address in (p, q):
                # 命中原始值槽前已知原输入为负；用步数恢复其幅值。
                recover = seq(self.constant(magnitude, -address),
                              self.add_into(magnitude, k) if operation == "@+" else self.subtract_from(magnitude, k),
                              self.constant(sign, 1), self.constant(run, 0))
                guards.append(self.once(self.read(run), self.if_zero(
                    probe + " " + "@+ " * -address, recover)))
            return seq(*guards, self.once(self.read(run), seq(
                f"&0 ^1 &{slot} ^5 &{slot} *1 {operation} ^5",
                self.if_zero(self.read(slot), finish(self.read(k), int(operation == "@+"))),
            )))

        race = seq(
            put_raw(q, self.read(p)), self.constant(magnitude, 0), self.constant(sign, 0),
            self.constant(k, 0), self.constant(run, 1),
            self.if_zero(self.read(p), self.constant(run, 0)),
            self.loop(self.read(run), seq(self.change(k, "@+"), advance(p, "@-"),
                                         self.once(self.read(run), advance(q, "@+")))),
            put_raw(q, "&0"),
        )
        ordinary = seq(
            self.constant(magnitude, -q), self.read(p) + " " + "@+ " * -q,
            "[", race, "&0", "]",
            put_raw(p, "&0"), select_raw(p),
        )
        return seq(
            self.constant(magnitude, -p), self.constant(sign, 1),
            select_raw(p), "@input ^5", self.read(p) + " " + "@+ " * -p,
            "[", ordinary, "&0", "]",
            # 两条路径均以 memory[0]=P、memory[P]=P 汇合，再统一清空。
            "&0 ^2 &0 ^1",
        )

    def subtract_from(self, destination, source):
        """要求目标不小于来源，保留来源。"""
        counter = self.slot("减法计数")
        if counter in (destination, source):
            raise ValueError("减法参数不能使用内部计数槽")
        return seq(self.copy(counter, source), self.loop(self.read(counter), seq(
            self.change(destination, "@-"), self.change(counter, "@-"))))

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
    # 首遍统计全部静态槽；第二遍把动态数据区放在槽位和两个锚点之后。
    preview = Macros()
    program(preview)
    macros = Macros(bound=len(preview.slots) + 3)
    code = program(macros)
    if macros.slots != preview.slots:
        raise ValueError("两遍生成的槽位布局不同")
    return format_code(code)
