"""加载固定版本的 PP3，并检查题库解答是否遵守执行约束。"""

from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "vendor" / "PP3"
if not (UPSTREAM / "src" / "pp3.py").is_file():
    raise RuntimeError("缺少 PP3 子模块，请运行 git submodule update --init --recursive")
sys.path.insert(0, str(UPSTREAM))

from src.pp3 import HandlerType, IRBuilder, Runtime, std_register


def catalog():
    return json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))


def problem(problem_id):
    for entry in catalog()["problems"]:
        if entry["id"].upper() == problem_id.upper():
            return entry
    raise ValueError(f"没有题目 {problem_id}")


def build(code):
    handles = IRBuilder(op_map=std_register).build(code)

    def check(nodes):
        for node in nodes:
            if node.TYPE == HandlerType.Mem:
                raise ValueError("题库解答禁止直接寻址")
            if node.TYPE == HandlerType.Loop:
                check(node.body)
            elif node.TYPE == HandlerType.InPlace and type(node) not in allowed_types:
                raise ValueError("题库解答禁止非标准操作")

    # 立即数也是原地 handler，需和标准注册的操作一并允许
    from src.pp3 import Data
    allowed_types = set(std_register.values()) | {Data}
    check(handles)
    return handles


def run_solution(problem_id):
    entry = problem(problem_id)
    if entry["status"] != "solved":
        raise ValueError(f"{entry['id']} 尚未完成，当前仅有题面和计划")
    code = (ROOT / entry["directory"] / "solution.pp3").read_text(encoding="ascii")
    Runtime(can_direct_addressing=False).run(build(code))
