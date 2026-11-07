"""对照旧主解测量原版 Runtime 的分派次数，不修改其执行语义。"""

from contextlib import redirect_stdout
from io import StringIO
import inspect
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.runtime import ROOT, Runtime, build, problem
from tools.generate import PROGRAMS
from tools.macros import compile_program


BASELINE = "a35bf1fc038177138e80d86c2e9c83d55f2d2b9a"


def dispatch_count(ir, stdin):
    lines, start = inspect.getsourcelines(Runtime.run)
    dispatch_line = start + next(i for i, line in enumerate(lines)
                                 if line.strip() == "if h.TYPE == HandlerType.Mem:")
    code = Runtime.run.__code__
    count = 0

    def trace(frame, event, arg):
        nonlocal count
        if frame.f_code is not code:
            return None
        if event == "line" and frame.f_lineno == dispatch_line:
            count += 1
        return trace

    previous = sys.gettrace()
    output = StringIO()
    try:
        with patch("sys.stdin", StringIO(stdin)), redirect_stdout(output):
            sys.settrace(trace)
            Runtime(can_direct_addressing=False).run(ir)
    finally:
        sys.settrace(previous)
    return count, output.getvalue()


def main():
    report = {
        "baseline": BASELINE,
        "metric": "原版 Runtime handler 分派次数；不等于宿主时间，循环内部实际执行计入",
        "scope": "有限样本对照，不据此推断任意输入的精确公式或普遍加速",
        "programs": {},
        "samples": [],
    }
    versions = {}
    for problem_id, program in PROGRAMS.items():
        path = problem(problem_id)["directory"] + "/solution.pp3"
        old = subprocess.run(["git", "show", f"{BASELINE}:{path}"], cwd=ROOT,
                             capture_output=True, check=True, encoding="ascii").stdout
        new = compile_program(program)
        report["programs"][problem_id] = {"old_tokens": len(old.split()), "new_tokens": len(new.split())}
        versions[problem_id] = build(old), build(new)

    def frame(text):
        return f"{len(text)}\n{text}"

    samples = [
        ("P003", "规范化负数", "-00123\n"), ("P004", "异号乘法", "-12\n7\n"),
        ("P005", "有符号GCD", "-84\n126\n"), ("P006", "文本旋转", frame("Hello, World!")),
        ("P008", "空白统计", frame("a b\nc\t")),
    ]
    for length in (0, 1, 8, 32, 128):
        samples.append(("P007", f"逆序{length}项", frame("".join(map(chr, reversed(range(length)))))))
    for length in (32, 128):
        samples.append(("P007", f"相等{length}项", frame("A" * length)))
    for problem_id, label, stdin in samples:
        old, new = versions[problem_id]
        old_count, old_output = dispatch_count(old, stdin)
        new_count, new_output = dispatch_count(new, stdin)
        if old_output != new_output:
            raise AssertionError(f"样本输出不同：{problem_id} {label}")
        report["samples"].append({"problem": problem_id, "label": label, "stdin": stdin,
                                  "old_dispatches": old_count, "new_dispatches": new_count})
        print(f"{problem_id} {label}: {old_count} -> {new_count}", flush=True)
    target = ROOT / "results" / "general-algorithms.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
