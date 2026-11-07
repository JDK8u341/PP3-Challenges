"""生命游戏与文本源码生成器；输入、演化和格式化全部在 PP3 内进行。"""

from pp3_toolkit import Arena, Chain, NegativeArray, compile_program, literal, seq
from pp3_toolkit.frames import ERROR_OUTPUT, frame_program
from pp3_toolkit.records import Reference


def text_to_pp3(m):
    data = NegativeArray(m)
    remaining, char = m.slot("生成.剩余"), m.slot("生成.字符")

    def finish(m, length):
        return seq(data.reset(), m.copy(remaining, length), m.loop(m.read(remaining), seq(
            m.put(char, data.read()), literal("&"), m.print_unsigned_decimal(char),
            literal(" @print_as_char\n"), data.advance(), m.change(remaining, "@-"))))

    return frame_program(m, lambda m, n: data.reset(),
                         lambda m, c: seq(data.put(m.read(c)), data.advance()), finish)


def game_of_life(m):
    heap = Arena(m)
    cells = Chain(heap, "棋盘", next_field=3)
    names = ("高度", "宽度", "代数", "输入符号", "错误", "格数", "剩余", "列剩余",
             "行剩余", "输入值", "节点", "行首", "行尾", "当前", "下方", "邻居", "邻居数", "继续")
    (height, width, generations, sign, error, count, remaining, columns, rows,
     value, node, first, last, current, below, neighbor, neighbors, run) = (
        m.slot(f"生命.{name}") for name in names)
    # 字段 1/2 是当前/下一代；3 是全局遍历；4/5/6/7 是东/西/北/南。
    input_cell = seq(
        m.decode_integer(value, sign),
        m.once(m.read(sign), m.constant(error, 1)),
        m.if_nonzero(m.read(value), m.if_nonzero(m.read(value) + " @-", m.constant(error, 1))),
        m.if_zero(m.read(error), seq(
            heap.allocate(node), heap.put(node, 1, m.read(value)), cells.append(node),
            m.if_nonzero(m.read(last), seq(heap.link(last, 4, node), heap.link(node, 5, last)),
                         Reference.copy(first, node)),
            Reference.copy(last, node), m.change(columns, "@-"),
            m.if_zero(m.read(columns), seq(
                heap.link(last, 4, first), heap.link(first, 5, last),
                Reference.put(last, "&0"), m.copy(columns, width))),
        )), m.change(remaining, "@-"),
    )
    vertical = seq(
        heap.link(cells.tail, 3, cells.head),
        Reference.copy(current, cells.head), Reference.copy(below, cells.head),
        m.copy(remaining, width), m.loop(m.read(remaining), seq(
            cells.advance(below), m.change(remaining, "@-"))),
        m.copy(remaining, count), m.loop(m.read(remaining), seq(
            heap.link(current, 7, below), heap.link(below, 6, current),
            cells.advance(current), cells.advance(below), m.change(remaining, "@-"))),
    )
    neighbor_steps = []
    # 八个方向是规则本身；不枚举棋盘尺寸、坐标或格值。
    for vertical_field, horizontal_field in ((6, 5), (6, 0), (6, 4), (0, 5), (0, 4), (7, 5), (7, 0), (7, 4)):
        neighbor_steps.append(seq(
            Reference.copy(neighbor, current),
            heap.follow(neighbor, neighbor, vertical_field) if vertical_field else "",
            heap.follow(neighbor, neighbor, horizontal_field) if horizontal_field else "",
            m.once(heap.read(neighbor, 1), m.change(neighbors, "@+")),
        ))
    update = seq(
        m.constant(neighbors, 0), *neighbor_steps, heap.put(current, 2, "&0"),
        m.if_zero(m.read(neighbors) + " @- @- @-", heap.put(current, 2, "&1")),
        m.if_zero(m.read(neighbors) + " @- @-", heap.put(current, 2, heap.read(current, 1))),
        cells.advance(current), m.change(remaining, "@-"),
    )
    generation = seq(
        Reference.copy(current, cells.head), m.copy(remaining, count),
        m.loop(m.read(remaining), update),
        Reference.copy(current, cells.head), m.copy(remaining, count),
        m.loop(m.read(remaining), seq(heap.put(current, 1, heap.read(current, 2)),
                                    cells.advance(current), m.change(remaining, "@-"))),
        m.change(generations, "@-"),
    )
    output = seq(
        Reference.copy(current, cells.head), m.copy(rows, height),
        m.loop(m.read(rows), seq(m.copy(columns, width), m.loop(m.read(columns), seq(
            heap.read(current, 1) + " " + "@+ " * 48 + "@print_as_char",
            cells.advance(current), m.change(columns, "@-"))),
            literal("\n"), m.change(rows, "@-"))),
    )
    headers = []
    for target in (height, width, generations):
        headers.extend((m.decode_integer(target, sign), m.once(m.read(sign), m.constant(error, 1))))
    valid = seq(
        heap.initialize(), m.conjunction(height, width, run),
        m.once(m.read(run), seq(
            m.copy(rows, height), m.loop(m.read(rows), seq(m.add_into(count, width), m.change(rows, "@-"))),
            m.copy(remaining, count), m.copy(columns, width), m.loop(m.read(remaining), input_cell))),
        m.if_nonzero(m.read(error), ERROR_OUTPUT, m.once(m.read(count), seq(
            vertical, m.loop(m.read(generations), generation), output))),
    )
    return seq(*headers, m.if_nonzero(m.read(error), ERROR_OUTPUT, valid))


PROGRAMS = {"P009": game_of_life, "P010": text_to_pp3}


def make_code(problem_id):
    return compile_program(PROGRAMS[problem_id])
