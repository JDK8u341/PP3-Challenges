# PP3 Challenges

用 PP3 解 Brainfuck 世界中的经典题目和挑战：算术、数列、文本、排序、模拟，以及解释器和代码生成。题面、推导和计划使用中文。

本仓库已完成**阶段 1**：收集 31 个候选、选出 12 个代表题，目前完成 5 题。包括归档的加法器和斐波那契，以及新增的十进制字符编解码、有符号乘法和 GCD。阶段 2 及之后的 7 题仍处于规划或研究阶段。

- [完整候选题库](research/catalog.md)
- [分阶段计划](ROADMAP.md)
- [执行条件与待确认语义](docs/semantics.md)
- [新题模板](templates/problem.md)
- [来源索引](research/sources.json)
- [机器可读题目目录](catalog.json)

## 首批题目

| 阶段 | 题目 | 状态 |
| --- | --- | --- |
| 0 | [P001 有符号 A+B](problems/P001-signed-add/) | 已完成，迁移 |
| 0 | [P002 斐波那契生成器](problems/P002-fibonacci/) | 已完成，迁移 |
| 1 | [P003 十进制字符输入输出](problems/P003-decimal-codec/) | 已完成 |
| 1 | [P004 有符号乘法器](problems/P004-signed-multiply/) | 已完成 |
| 1 | [P005 最大公约数](problems/P005-gcd/) | 已完成 |
| 2 | [P006 ROT13](problems/P006-rot13/) | 待开始 |
| 2 | [P007 字节排序](problems/P007-byte-sort/) | 待开始 |
| 2 | [P008 wc 统计](problems/P008-wc/) | 待开始 |
| 3 | [P009 生命游戏](problems/P009-game-of-life/) | 待开始 |
| 3 | [P010 文本到 PP3 代码生成器](problems/P010-text-to-pp3/) | 待开始 |
| 4 | [P011 用 PP3 写 BF 解释器](problems/P011-brainfuck-interpreter/) | 待开始 |
| 5 | [P012 PP3 子集自解释器](problems/P012-pp3-self-interpreter/) | 研究目标 |

状态以 [catalog.json](catalog.json) 为准。已有两题在“禁用直接寻址、原有四种标准操作”条件下完成；字符 I/O 是之后题目的可用能力。

## 运行已有解答

```text
git clone --recurse-submodules https://github.com/JDK8u341/PP3-Challenges.git
cd PP3-Challenges
python tools/run.py P001
python tools/run.py P002
python tools/run.py P003
python tools/run.py P004
python tools/run.py P005
python -B -m unittest discover -v
```

PP3 作为子模块固定在提交 `aceb4c532cf475f7b69fb623affc81c9f70e8c48`。已有普通 clone 可先运行 `git submodule update --init --recursive`。

P001 分两行输入 A、B，输出它们的和。P002 输入非负项数，从 `1, 1` 开始逐项输出，输入 0 不输出。

P003 读取一行可选符号的 ASCII 十进制整数，输出规范化文本，非法输入输出 `ERROR`。P004、P005 都读取两行整数，分别输出乘积和非负最大公约数。所有题目仍禁用直接寻址。

阶段 1 的中文证明见 [共同宏与不变量](docs/stage1-macros.md) 和各题的 `proof.md`。重新生成这三题的纯 DSL：

```text
python tools/generate.py all
```

运行器始终采用 `IRBuilder(op_map=std_register)` 和 `Runtime(can_direct_addressing=False)`。Python 工具只负责加载、展开静态宏和测试，不参与被解题目的运算；新解答不能调用 cup 或注入自定义运算。

## 目录

```text
research/       题目调研、来源与筛选依据
docs/           语义、验证与贡献约定
problems/Pxxx/  每题题面、纯 DSL 解答、中文推导、样例
templates/      新题文档模板
tools/          运行与验证工具
tests/          目录一致性和已完成题回归测试
vendor/PP3/     固定版本的上游运行器子模块
```

## 来源与许可

外部 BF 程序仅作为参考链接；题面以中文重新描述并明确 PP3 改编范围，不复制第三方完整解答。新增原创代码和文档采用 GPL-3.0，见 [LICENSE](LICENSE)。PP3 子模块及任何后续引入的第三方材料保留各自许可和署名；链接不代表第三方内容变更许可。
