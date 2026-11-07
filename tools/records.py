"""从 PP3-Lab 的局部路由记录移植的链表宏；运行时只执行生成的 DSL。"""

from tools.macros import seq


class Reference:
    """零或永久零头地址；引用赋值不能使用普通自然数赋值宏。"""

    @staticmethod
    def put(slot, expression):
        return f"&0 ^1 &{slot} ^3 &{slot} ^1 {expression} ^3"

    @staticmethod
    def copy(destination, source):
        return "" if destination == source else Reference.put(destination, f"&{source} ~1")

    @staticmethod
    def next(slot):
        return f"&0 ^1 &{slot} ^3 &{slot} *1 @- @- @- ~1 ^3"

    @staticmethod
    def bump(slot):
        return f"&0 ^1 &{slot} ^3 &{slot} *1 @- @- @- @- ^3"


class RecordHeap:
    MAGNITUDE = 1
    SIGN = 2
    NEXT = 3

    def __init__(self, macros):
        self.m = macros
        self.bump = macros.slot("记录堆.未使用地址")

    def initialize(self):
        return Reference.put(self.bump, f"&{self.m.array_base}")

    def field_address(self, reference, field):
        if field not in (self.MAGNITUDE, self.SIGN, self.NEXT):
            raise ValueError("永久零头不可写")
        return self.m.read(reference) + " " + "@- " * field

    def read(self, reference, field):
        return self.field_address(reference, field) + "~1"

    def put(self, reference, field, expression):
        address = self.field_address(reference, field)
        depth = 3 if field == self.NEXT else 4
        return f"&0 ^1 {address} ^{depth} {address} ^1 {expression} ^{depth}"

    def allocate(self, node, magnitude, sign):
        if len({node, magnitude, sign, self.bump}) != 4:
            raise ValueError("分配器、节点引用和载荷必须使用不同槽")
        return seq(
            Reference.copy(node, self.bump), Reference.bump(self.bump),
            self.put(node, self.MAGNITUDE, self.m.read(magnitude)),
            self.put(node, self.SIGN, self.m.read(sign)), self.put(node, self.NEXT, "&0"),
        )


class RecordList:
    """线性链拥有独立头尾；弹出节点后才允许接入另一链。"""

    def __init__(self, heap, name):
        self.heap = heap
        self.m = heap.m
        self.head = self.m.slot(f"{name}.表头")
        self.tail = self.m.slot(f"{name}.表尾")

    def _check_node(self, node):
        if node in (self.head, self.tail):
            raise ValueError("节点工作引用不能覆盖头尾")

    def append(self, node):
        self._check_node(node)
        return seq(self.m.if_nonzero(
            self.m.read(self.tail), self.heap.put(self.tail, RecordHeap.NEXT, self.m.read(node)),
            Reference.copy(self.head, node)), Reference.copy(self.tail, node))

    def pop(self, node):
        self._check_node(node)
        return seq(
            Reference.copy(node, self.head), Reference.next(self.head),
            self.m.if_zero(self.m.read(self.head), Reference.put(self.tail, "&0")),
            self.heap.put(node, RecordHeap.NEXT, "&0"),
        )

    def concat(self, other):
        if self.heap is not other.heap or {self.head, self.tail} & {other.head, other.tail}:
            raise ValueError("拼接要求同堆、不同控制槽和互不重叠的节点所有权")
        join = seq(self.m.if_nonzero(
            self.m.read(self.tail), self.heap.put(self.tail, RecordHeap.NEXT, self.m.read(other.head)),
            Reference.copy(self.head, other.head)), Reference.copy(self.tail, other.tail))
        return seq(self.m.once(self.m.read(other.head), join),
                   Reference.put(other.head, "&0"), Reference.put(other.tail, "&0"))


def merge_sort(m, source, length, name="归并"):
    """稳定的自底向上归并排序；数据幅值为任意自然数，不依赖字节值域。"""
    heap = source.heap
    output, left, right = (RecordList(heap, f"{name}.{part}") for part in ("输出", "左段", "右段"))
    width, count, node, run, a, b, lt, eq, gt = (m.slot(f"{name}.{part}") for part in (
        "段长", "截取剩余", "转移节点", "继续", "左值", "右值", "小于", "等于", "大于"))

    def split(target):
        return seq(m.copy(count, width), m.conjunction(count, source.head, run),
                   m.loop(m.read(run), seq(source.pop(node), target.append(node),
                          m.change(count, "@-"), m.conjunction(count, source.head, run))))

    def take(target):
        return seq(target.pop(node), output.append(node))

    merge = seq(
        m.conjunction(left.head, right.head, run),
        m.loop(m.read(run), seq(
            m.put(a, heap.read(left.head, RecordHeap.MAGNITUDE)),
            m.put(b, heap.read(right.head, RecordHeap.MAGNITUDE)), m.compare(a, b, lt, eq, gt),
            # 相等时取左段，保持相同载荷节点的原始先后次序。
            m.if_nonzero(m.read(gt), take(right), take(left)),
            m.conjunction(left.head, right.head, run),
        )), output.concat(left), output.concat(right),
    )
    one_pass = seq(
        m.loop(m.read(source.head), seq(split(left), split(right), merge)),
        source.concat(output), m.add_into(width, width), m.compare(width, length, lt, eq, gt),
    )
    return seq(m.constant(width, 1), m.compare(width, length, lt, eq, gt),
               m.loop(m.read(lt), one_pass))
