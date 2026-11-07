"""纯 PP3 Brainfuck 解释器：静态展开八种操作，动态执行客体程序。"""

from pp3_toolkit import InstructionMachine, compile_program, dual_frame, seq
from pp3_toolkit.records import Reference


def brainfuck(m):
    machine = InstructionMachine(m)
    heap = machine.heap
    tape, adjacent, value, recognized = (m.slot(f"BF.{part}") for part in ("带指针", "相邻格", "格值", "有效指令"))

    def code_char(m, char, error):
        return seq(
            m.constant(recognized, 0),
            *(m.if_zero(m.read(char) + " " + "@- " * ord(op), m.constant(recognized, 1)) for op in "><+-.,[]"),
            m.once(m.read(recognized), machine.emit(char, error, ord("["), ord("]"))),
        )

    def move(field, opposite):
        return seq(heap.follow(adjacent, tape, field), m.if_zero(m.read(adjacent), seq(
            heap.allocate(adjacent), heap.link(tape, field, adjacent), heap.link(adjacent, opposite, tape))),
            Reference.copy(tape, adjacent))

    def finish(m, error):
        increment = seq(
            m.put(value, heap.read(tape, 1)),
            m.if_nonzero(m.read(value) + " " + "@- " * 255, m.change(value, "@+"), m.constant(value, 0)),
            heap.put(tape, 1, m.read(value)),
        )
        decrement = seq(
            m.put(value, heap.read(tape, 1)),
            m.if_nonzero(m.read(value), m.change(value, "@-"), m.constant(value, 255)),
            heap.put(tape, 1, m.read(value)),
        )
        read = m.if_nonzero(m.read(machine.input), seq(
            heap.put(tape, 1, heap.read(machine.input, 1)), machine.data.advance(machine.input)),
            heap.put(tape, 1, "&0"))
        operations = {
            ">": move(5, 4), "<": move(4, 5), "+": increment, "-": decrement,
            ".": heap.read(tape, 1) + " @print_as_char", ",": read,
            "[": m.if_zero(heap.read(tape, 1), machine.jump_after_pair()),
            "]": m.once(heap.read(tape, 1), machine.jump_after_pair()),
        }
        dispatch = seq(*(m.if_zero(m.read(machine.opcode) + " " + "@- " * ord(op), body)
                         for op, body in operations.items()))
        return machine.run(error, heap.allocate(tape), dispatch)

    return dual_frame(m, lambda m, error: heap.initialize(), code_char,
                      lambda m, error: machine.code_end(error),
                      lambda m, char, error: machine.data_char(char), finish)


PROGRAMS = {"P011": brainfuck}


def make_code(problem_id):
    return compile_program(PROGRAMS[problem_id])
