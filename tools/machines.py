"""解释器共用的零头记录、链和双字符帧；这里只展开静态 DSL。"""

from tools.macros import seq
from tools.records import Reference
from tools.stage2 import ERROR_OUTPUT, validate_byte


class Arena:
    """固定宽度记录：头永久为零，字段分别声明自然数或零头引用。"""

    def __init__(self, m, width=8):
        self.m, self.width = m, width
        self.bump = m.slot("机器堆.未使用地址")

    def initialize(self):
        return Reference.put(self.bump, f"&{self.m.array_base}")

    def address(self, node, field):
        if not 1 <= field <= self.width:
            raise ValueError("字段必须位于记录内部，不能覆盖零头")
        return self.m.read(node) + " " + "@- " * field

    def read(self, node, field):
        return self.address(node, field) + "~1"

    def put(self, node, field, expression, *, reference=False):
        address = self.address(node, field)
        depth = 3 if reference else 4
        return f"&0 ^1 {address} ^{depth} {address} ^1 {expression} ^{depth}"

    def link(self, node, field, target):
        return self.put(node, field, self.m.read(target), reference=True)

    def allocate(self, node):
        if node == self.bump:
            raise ValueError("分配结果不能覆盖分配游标")
        # 新区域从未写入，全部字段已隐式为零；分配只移动零头引用。
        bump = self.bump
        return seq(Reference.copy(node, bump),
                   f"&0 ^1 &{bump} ^3 &{bump} *1 " + "@- " * (self.width + 1) + "^3")

    def follow(self, destination, source, field):
        if destination == source:
            # 先交换取出旧引用；普通赋值会先把该控制槽改成自环。
            self.address(source, field)
            return f"&0 ^1 &{source} ^3 &{source} *1 " + "@- " * field + "~1 ^3"
        return Reference.put(destination, self.read(source, field))


class Chain:
    """可保留节点的只追加链；遍历不拆除边，适合指令流和输入缓冲。"""

    def __init__(self, arena, name, next_field=8):
        self.heap, self.m, self.next_field = arena, arena.m, next_field
        self.head, self.tail = (self.m.slot(f"{name}.{part}") for part in ("表头", "表尾"))

    def append(self, node):
        if node in (self.head, self.tail):
            raise ValueError("追加节点不能覆盖链表控制槽")
        return seq(self.m.if_nonzero(
            self.m.read(self.tail), self.heap.link(self.tail, self.next_field, node),
            Reference.copy(self.head, node)), Reference.copy(self.tail, node))

    def advance(self, pointer):
        return self.heap.follow(pointer, pointer, self.next_field)


class InstructionMachine:
    """平坦指令链：1 操作码，2/3 参数，4 配对括号，5 括号栈，8 后继。"""

    def __init__(self, m):
        self.m, self.heap = m, Arena(m)
        self.code, self.data = Chain(self.heap, "客体代码"), Chain(self.heap, "客体输入")
        (self.node, self.stack, self.pc, self.active, self.opcode, self.input) = (
            m.slot(f"机器.{part}") for part in ("节点", "括号栈", "PC", "当前指令", "操作码", "输入游标"))

    def emit(self, opcode, error, opening, closing, magnitude=None, sign=None):
        m, heap, node = self.m, self.heap, self.node
        pair = seq(heap.link(node, 4, self.stack), heap.link(self.stack, 4, node),
                   heap.follow(self.stack, self.stack, 5))
        return seq(
            heap.allocate(node), heap.put(node, 1, m.read(opcode)),
            heap.put(node, 2, m.read(magnitude)) if magnitude is not None else "",
            heap.put(node, 3, m.read(sign)) if sign is not None else "",
            self.code.append(node),
            m.if_zero(m.read(opcode) + " " + "@- " * opening, seq(
                heap.link(node, 5, self.stack), Reference.copy(self.stack, node))),
            m.if_zero(m.read(opcode) + " " + "@- " * closing,
                      m.if_nonzero(m.read(self.stack), pair, m.constant(error, 1))),
        )

    def code_end(self, error):
        return self.m.once(self.m.read(self.stack), self.m.constant(error, 1))

    def data_char(self, char):
        return seq(self.heap.allocate(self.node), self.heap.put(self.node, 1, self.m.read(char)),
                   self.data.append(self.node))

    def jump_after_pair(self):
        return seq(self.heap.follow(self.pc, self.active, 4), self.code.advance(self.pc))

    def run(self, error, initialize, dispatch):
        m = self.m
        return seq(
            Reference.copy(self.pc, self.code.head), Reference.copy(self.input, self.data.head), initialize,
            m.loop(m.read(self.pc), seq(
                Reference.copy(self.active, self.pc),
                m.put(self.opcode, self.heap.read(self.active, 1)), self.code.advance(self.pc), dispatch,
                m.once(m.read(error), Reference.put(self.pc, "&0")),
            )), m.once(m.read(error), ERROR_OUTPUT),
        )


def literal(text):
    return " ".join(f"&{ord(char)} @print_as_char" for char in text)


def dual_frame(m, prepare, code_char, code_end, data_char, finish):
    """先读取两个整数长度，再连续消费源码帧和数据帧，成功后才执行。"""
    code_length, data_length, code_sign, data_sign, left, char, error = (
        m.slot(f"双帧.{part}") for part in (
            "源码长度", "数据长度", "源码负号", "数据负号", "剩余", "字符", "错误"))
    initialization = prepare(m, error)
    code_step, end, data_step, execution = (
        code_char(m, char, error), code_end(m, error),
        data_char(m, char, error), finish(m, error))

    def load(length, body):
        return seq(m.copy(left, length), m.loop(m.read(left), seq(
            m.put(char, "@input_as_char"),
            m.if_zero(m.read(error), seq(validate_byte(m, char, error),
                                        m.if_zero(m.read(error), body))),
            m.change(left, "@-"))))

    return seq(
        m.decode_integer(code_length, code_sign), m.decode_integer(data_length, data_sign),
        m.if_nonzero(m.read(code_sign), m.constant(error, 1)),
        m.if_nonzero(m.read(data_sign), m.constant(error, 1)),
        m.if_nonzero(m.read(error), ERROR_OUTPUT, seq(
            initialization, load(code_length, code_step),
            m.if_zero(m.read(error), end), load(data_length, data_step),
            m.if_nonzero(m.read(error), ERROR_OUTPUT, execution))),
    )
