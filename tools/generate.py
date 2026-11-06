"""生成阶段一的纯 DSL 文件；不读取题目输入。"""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.runtime import ROOT, problem
from tools.stage1 import PROGRAMS, make_code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("problem_id", choices=[*PROGRAMS, "all"])
    args = parser.parse_args()
    ids = PROGRAMS if args.problem_id == "all" else [args.problem_id]
    for problem_id in ids:
        target = ROOT / problem(problem_id)["directory"] / "solution.pp3"
        target.write_text(make_code(problem_id), encoding="ascii")
        print(target.relative_to(ROOT))


if __name__ == "__main__":
    main()
