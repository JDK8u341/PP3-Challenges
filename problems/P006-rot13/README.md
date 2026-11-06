# P006：ROT13 编解码器

状态：已规划，尚未实现；阶段：2。

## 题目

变换 ASCII A–Z 与 a–z；其他有效字符保持不变。

输入输出规约：定长字符帧（草案）。以上为 PP3 改编题的草案，开题前确认未决规则，不改动 PP3 本身。

## 解题计划

将字母映射分成四个区间，用零测试构造分支；避免把 EOF 当 0。

依赖：P003。

## 验收要点

空文本、大小写边界 A/N/Z/a/n/z、标点、换行；两次变换还原。

运行条件：禁用直接寻址，使用固定版本 PP3 的 `std_register`；不使用 cup 或自定义宿主运算替代解题。

## 参考来源

- [S01：Daniel B. Cristofani 的 Brainfuck 程序目录](https://brainfuck.org/)
- [S11：小型 Brainfuck 程序集](https://github.com/4ffy/brainfuck-programs)

原始 BF 题或程序仅提供思路；本页定义的是 PP3 改编目标，不保证输入范围、终止协议和原程序完全一致。
