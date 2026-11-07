"""PP3 核心子集的自解释器；客体整数与地址都用符号、幅值表示。"""

from pp3_toolkit import Chain, InstructionMachine, compile_program, dual_frame, seq
from pp3_toolkit.records import Reference


def self_interpreter(m):
    machine = InstructionMachine(m)
    heap = machine.heap
    token = Chain(heap, "词法单词")
    memory = Chain(heap, "客体内存")
    names = ("词法节点", "词法游标", "首字符", "数字字符", "数字个数", "参数幅值", "参数负号",
             "解析操作码", "ASCII空白", "匹配游标", "匹配成功", "匹配字符", "view幅值", "view负号",
             "地址幅值", "地址负号", "查找游标", "内存单元", "键幅值", "键负号", "幅值匹配", "符号匹配",
             "键匹配", "剩余深度", "交换幅值", "交换负号", "间接指令", "模数", "商", "余数", "输出字符")
    (node, cursor, first, digit, digits, argument, negative, opcode, blank, text_pointer, matched, char,
     vm, vs, am, ass, scan, cell, key_m, key_s, match_m, match_s, match, depth, old_m, old_s,
     indirect, modulus, quotient, remainder, output_char) = (m.slot(f"自解释.{name}") for name in names)

    def match_literal(text, operation):
        steps = []
        for expected in text:
            steps.append(m.if_nonzero(m.read(text_pointer), seq(
                m.put(char, heap.read(text_pointer, 1)),
                m.if_nonzero(m.read(char) + " " + "@- " * ord(expected), m.constant(matched, 0)),
                token.advance(text_pointer)), m.constant(matched, 0)))
        return seq(Reference.copy(text_pointer, token.head), m.constant(matched, 1), *steps,
                   m.once(m.read(text_pointer), m.constant(matched, 0)),
                   m.once(m.read(matched), m.constant(opcode, operation)))

    def parse(error):
        sign = seq(
            m.put(digit, heap.read(cursor, 1)),
            m.if_zero(m.read(digit) + " " + "@- " * 45,
                      seq(m.constant(negative, 1), token.advance(cursor))),
            m.if_zero(m.read(digit) + " " + "@- " * 43, token.advance(cursor)),
        )
        numeric = seq(
            m.once(m.read(cursor), sign),
            m.loop(m.read(cursor), seq(
                m.put(digit, heap.read(cursor, 1)), m.in_range(digit, 48, 57, matched),
                m.if_nonzero(m.read(matched), seq(
                    m.put(digit, heap.read(cursor, 1) + " " + "@- " * 48),
                    m.multiply_by_ten(argument), m.add_into(argument, digit), m.change(digits, "@+")),
                    m.constant(error, 1)), token.advance(cursor))),
            m.if_zero(m.read(digits), m.constant(error, 1)),
            m.if_nonzero(m.read(opcode) + " @-", seq(
                m.once(m.read(negative), m.constant(error, 1)),
                m.if_zero(m.read(argument), m.constant(error, 1)))),
            m.if_zero(m.read(argument), m.constant(negative, 0)),
        )
        body = seq(
            Reference.copy(cursor, token.head), m.put(first, heap.read(cursor, 1)), token.advance(cursor),
            m.constant(opcode, 0), m.constant(argument, 0), m.constant(negative, 0), m.constant(digits, 0),
            *(m.if_zero(m.read(first) + " " + "@- " * ord(prefix), m.constant(opcode, operation))
              for prefix, operation in (("&", 1), ("~", 2), ("^", 3), ("*", 4))),
            m.once(m.read(opcode), numeric),
            *(m.if_zero(m.read(first) + " " + "@- " * ord(bracket),
                        m.if_zero(m.read(cursor), m.constant(opcode, operation)))
              for bracket, operation in (("[", 5), ("]", 6))),
            m.if_zero(m.read(first) + " " + "@- " * 64, seq(
                match_literal("@+", 7), match_literal("@-", 8),
                match_literal("@input_as_char", 9), match_literal("@print_as_char", 10))),
            m.if_zero(m.read(opcode), m.constant(error, 1)),
            m.if_zero(m.read(error), machine.emit(opcode, error, 5, 6, argument, negative)),
            Reference.put(token.head, "&0"), Reference.put(token.tail, "&0"),
        )
        return m.once(m.read(token.head), body)

    def code_char(m, source_char, error):
        return seq(
            m.in_range(source_char, 9, 13, blank),
            m.if_zero(m.read(source_char) + " " + "@- " * 32, m.constant(blank, 1)),
            m.if_nonzero(m.read(blank), parse(error), seq(
                heap.allocate(node), heap.put(node, 1, m.read(source_char)), token.append(node))),
        )

    def lookup():
        # 用实际访问过的键建表；地址的幅值不会成为宿主内存地址。
        return seq(
            Reference.copy(scan, memory.head), Reference.put(cell, "&0"),
            m.loop(m.read(scan), seq(
                m.put(key_m, heap.read(scan, 1)), m.put(key_s, heap.read(scan, 2)),
                m.equal(key_m, am, match_m), m.equal(key_s, ass, match_s),
                m.conjunction(match_m, match_s, match),
                m.if_nonzero(m.read(match), seq(Reference.copy(cell, scan), Reference.put(scan, "&0")),
                             memory.advance(scan)),
            )),
            m.if_zero(m.read(cell), seq(
                heap.allocate(cell), heap.put(cell, 1, m.read(am)), heap.put(cell, 2, m.read(ass)),
                memory.append(cell))),
        )

    def finish(m, error):
        increment = m.if_nonzero(m.read(vs), seq(
            m.change(vm, "@-"), m.if_zero(m.read(vm), m.constant(vs, 0))), m.change(vm, "@+"))
        decrement = m.if_nonzero(m.read(vs), m.change(vm, "@+"), m.if_nonzero(m.read(vm),
            m.change(vm, "@-"), seq(m.constant(vm, 1), m.constant(vs, 1))))
        routing = seq(
            m.copy(am, vm), m.copy(ass, vs), m.put(depth, heap.read(machine.active, 2)), m.change(depth, "@-"),
            m.loop(m.read(depth), seq(lookup(), m.put(am, heap.read(cell, 3)),
                                    m.put(ass, heap.read(cell, 4)), m.change(depth, "@-"))), lookup(),
            m.if_zero(m.read(machine.opcode) + " @- @-", seq(
                m.put(vm, heap.read(cell, 3)), m.put(vs, heap.read(cell, 4)))),
            m.if_zero(m.read(machine.opcode) + " @- @- @-", seq(
                heap.put(cell, 3, m.read(vm)), heap.put(cell, 4, m.read(vs)))),
            m.if_zero(m.read(machine.opcode) + " @- @- @- @-", seq(
                m.put(old_m, heap.read(cell, 3)), m.put(old_s, heap.read(cell, 4)),
                heap.put(cell, 3, m.read(vm)), heap.put(cell, 4, m.read(vs)),
                m.copy(vm, old_m), m.copy(vs, old_s))),
        )
        read = m.if_nonzero(m.read(machine.input), seq(
            m.put(vm, heap.read(machine.input, 1)), m.constant(vs, 0), machine.data.advance(machine.input)),
            m.constant(error, 1))
        write = seq(
            m.constant(modulus, 256), m.divmod_unsigned(vm, modulus, quotient, remainder),
            m.copy(output_char, remainder), m.once(m.read(vs), m.once(m.read(remainder), seq(
                m.constant(output_char, 256), m.subtract_from(output_char, remainder)))),
            m.read(output_char) + " @print_as_char",
        )
        operations = {
            1: seq(m.put(vm, heap.read(machine.active, 2)), m.put(vs, heap.read(machine.active, 3))),
            5: m.if_zero(m.read(vm), machine.jump_after_pair()),
            6: m.once(m.read(vm), machine.jump_after_pair()),
            7: increment, 8: decrement, 9: read, 10: write,
        }
        dispatch = seq(
            m.in_range(machine.opcode, 2, 4, indirect), m.once(m.read(indirect), routing),
            *(m.if_zero(m.read(machine.opcode) + " " + "@- " * operation, body)
              for operation, body in operations.items()),
        )
        return machine.run(error, "", dispatch)

    return dual_frame(m, lambda m, error: heap.initialize(), code_char,
                      lambda m, error: seq(parse(error), machine.code_end(error)),
                      lambda m, source_char, error: machine.data_char(source_char), finish)


PROGRAMS = {"P012": self_interpreter}


def make_code(problem_id):
    return compile_program(PROGRAMS[problem_id])
