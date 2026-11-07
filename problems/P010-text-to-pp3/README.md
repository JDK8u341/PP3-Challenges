# P010：文本到 PP3 代码生成器

状态：已完成；阶段：3。题面于 2026-11-07 确认，为 PP3 改编。

## 题目

PP3 程序读取文本并输出 PP3 源码；执行生成源码后应还原输入文本。

沿用[阶段二字符帧](../../docs/stage2-frames.md)：首行用 `@input` 读取非负长度 n，再精确读取 n 个码点在 0..255 的字符，补回 LF 计入帧长。负长度或完整帧内非法码点输出 `ERROR\n`；提前 EOF 保留异常，均不会输出部分源码。

成功时为每个字符输出一行 `&十进制码点 @print_as_char`。空帧输出空源码。NUL、换行、引号、反斜杠等都通过立即数表示，不需要源码字符串转义。

## 解答

纯 DSL：[solution.pp3](solution.pp3)；静态生成器：`tools/stage3.py` 的 `text_to_pp3`；[证明](proof.md)、[样例](cases.json)。

PP3 自己缓存并验证帧，逐位格式化码点，再输出源码；Python 只展开该生成器的固定程序。执行时 Python 不参与待转换文本的解题。

测试将生成结果重新送入原版 PP3 编译、执行，覆盖全部 256 个码点、随机帧和特殊字符；部分结果也交给 P012 执行。当前完成的是正确性基线，没有声称实现最短源码优化。依赖：P003、P006。

运行条件：禁用直接寻址，使用固定版本 PP3 的 `std_register`；不使用 cup 或自定义宿主运算替代解题。

## 参考来源

- [S07：Brainfuck Golf 0：输入文本，输出打印该文本的程序](https://sange.fi/esoteric/brainfuck/bf-golf-results/results0.txt)
- [S02：小型 Brainfuck 程序与 Golf 题解](https://brainfuck.org/short.b)

原始 BF 题或程序仅提供思路；本页定义的是 PP3 改编目标，不保证输入范围、终止协议和原程序完全一致。
