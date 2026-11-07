# 通用生成工具迁移

通用的静态 DSL 实现现由独立 Python 包 [PP3-Toolkit](https://github.com/JDK8u341/PP3-Toolkit) 拥有。本仓库不再维护第二份宏/记录实现；生成器直接导入 `pp3_toolkit`，运行时仍是固定 PP3 子模块。

## 包含与保留

已提取：`Macros`、两遍 `compile_program`、自然数和符号/幅值宏、`NegativeArray`、`Reference`、`RecordHeap`、`RecordList`、稳定 `merge_sort`、可配置 `Arena`、`Chain`、`InstructionMachine`、`frame_program`、`dual_frame`、固定文本输出与字节校验。

保留在 Challenges：P003–P012 的题目算法和程序构造，例如数字 codec、GCD、ROT13、生命游戏、BF/PP3 解释器。它们是应用这些构件的示例，不属于通用库 API。

## 安装和重建

`requirements-test.txt` 指向 toolkit 仓库已合并的完整 Git commit，不依赖浮动分支或 PyPI。要运行测试或调用 `tools/generate.py`：

```powershell
python -m pip install -r requirements-test.txt
python -B -m unittest discover -v
python tools/generate.py all
```

普通运行已生成的 `.pp3` 文件不需要导入 Python 宏包；PP3 子模块仍按根目录文档初始化。

## 旧路径兼容

`tools.macros`、`tools.arrays`、`tools.records` 和 `tools.machines` 仅 re-export 新包符号，供现有消费者平滑迁移。新代码应直接从 `pp3_toolkit` 或其子模块导入。测试检查新旧路径解析到相同 Python 对象。

## 实现机制

宏不是 host-side evaluator。Python 在固定生成器上声明静态槽与代码片段；两遍扫描把数组/堆放在静态槽下方。执行时，零锚点与 `~`/`^`/`*` 间接路径构成图路由；零头记录区分节点身份和载荷；引用与自然数载荷使用不同寻址深度。更细推导与成本边界见 Toolkit 的[机制文档](https://github.com/JDK8u341/PP3-Toolkit/blob/main/docs/mechanism.md)，底层性质实验见 [PP3-Lab](https://github.com/JDK8u341/PP3-Lab)。
