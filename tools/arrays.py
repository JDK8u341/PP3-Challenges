"""负地址数组的静态宏；指针与非负元素分别采用不同寻址深度。"""

from tools.macros import seq


class NegativeArray:
    def __init__(self, macros, name="数据区"):
        self.m = macros
        self.name = name
        self.pointer = macros.slot(f"{name}.指针")

    @property
    def base(self):
        return -self.m.bound

    def reset(self):
        # 元素可能经过正地址标记，指针到零最多四步。
        p = self.pointer
        return f"&0 ^1 &{p} ^5 &{p} ^1 &{self.base} ^5"

    def advance(self):
        # 数据地址向负方向增长；四次跳转以指针自环补齐路径。
        p = self.pointer
        return f"&0 ^1 &{p} ^5 &{p} *1 @- ^5"

    def read(self):
        return f"&{self.pointer} ~1 ~1"

    def put(self, expression):
        # 目标建立自环；表达式不得读取目标旧值或破坏零槽。
        p = self.pointer
        return f"&0 ^1 &{p} ~1 ^4 &{p} ~1 ^1 {expression} ^4"

    def change(self, operation):
        if operation not in ("@+", "@-"):
            raise ValueError("数组更新只接受自增或自减")
        p = self.pointer
        return f"&0 ^1 &{p} ~1 ^4 &{p} ~1 *1 {operation} ^4"

    def seek(self, index):
        counter = self.m.slot(f"{self.name}.寻址计数")
        if index in (counter, self.pointer):
            raise ValueError("数组下标不能使用指针槽或内部计数槽")
        return seq(
            self.m.copy(counter, index), self.reset(),
            self.m.loop(self.m.read(counter), seq(self.advance(), self.m.change(counter, "@-"))),
        )
