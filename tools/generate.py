"""生成阶段一、二的纯 DSL 文件；不读取题目输入。"""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.runtime import ROOT, problem
from tools.macros import compile_program
from tools.stage1 import PROGRAMS as STAGE1
from tools.stage2 import PROGRAMS as STAGE2

PROGRAMS = {**STAGE1, **STAGE2}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("problem_id", choices=[*PROGRAMS, "all"])
    args = parser.parse_args()
    ids = PROGRAMS if args.problem_id == "all" else [args.problem_id]
    for problem_id in ids:
        target = ROOT / problem(problem_id)["directory"] / "solution.pp3"
        target.write_text(compile_program(PROGRAMS[problem_id]), encoding="ascii")
        print(target.relative_to(ROOT))


if __name__ == "__main__":
    main()
