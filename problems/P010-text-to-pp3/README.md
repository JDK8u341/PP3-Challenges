# P010：文本到 PP3 代码生成器

状态：已规划，尚未实现；阶段：3。

## 题目

PP3 程序读取文本并输出 PP3 源码；执行生成源码后应还原输入文本。

输入输出规约：定长字符帧（草案）。以上为 PP3 改编题的草案，开题前确认未决规则，不改动 PP3 本身。

## 解题计划

先生成 &n @print_as_char 基线；再比较重复输出、差分与循环的长度和执行成本。

依赖：P003、P006。

## 验收要点

空文本、NUL、换行、引号；必须重新编译并执行生成源码做往返验证。

运行条件：禁用直接寻址，使用固定版本 PP3 的 `std_register`；不使用 cup 或自定义宿主运算替代解题。

## 参考来源

- [S07：Brainfuck Golf 0：输入文本，输出打印该文本的程序](https://sange.fi/esoteric/brainfuck/bf-golf-results/results0.txt)
- [S02：小型 Brainfuck 程序与 Golf 题解](https://brainfuck.org/short.b)

原始 BF 题或程序仅提供思路；本页定义的是 PP3 改编目标，不保证输入范围、终止协议和原程序完全一致。
