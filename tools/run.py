"""按题目编号运行已完成的纯 PP3 解答。"""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.runtime import run_solution


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("problem_id", help="题目编号，例如 P001")
    args = parser.parse_args()
    try:
        run_solution(args.problem_id)
    except ValueError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
