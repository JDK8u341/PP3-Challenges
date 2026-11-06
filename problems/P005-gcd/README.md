# P005：最大公约数

状态：已规划，尚未实现；阶段：1。

## 题目

输出非负 gcd(A,B)，拟约定 gcd(0,0)=0。

输入输出规约：整数行输入（草案）。以上为 PP3 改编题的草案，开题前确认未决规则，不改动 PP3 本身。

## 解题计划

先实现比较与非负余数，再做欧几里得算法；可先用减法版本验证。

依赖：P001、P004。

## 验收要点

(0,0)、单零、相等、互质、负输入；具体输入范围开题时确认。

运行条件：禁用直接寻址，使用固定版本 PP3 的 `std_register`；不使用 cup 或自定义宿主运算替代解题。

## 参考来源

- [S05：欧几里得除法](http://brainfuckhowto.blogspot.com/2017/02/euclidean-division.html)
- [S12：Brainfuck GCD(sigma(N), N) 挑战](https://github.com/harbor-framework/terminal-bench-3/pull/91)

原始 BF 题或程序仅提供思路；本页定义的是 PP3 改编目标，不保证输入范围、终止协议和原程序完全一致。
