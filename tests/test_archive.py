"""检查目录、来源、生成结果与现有纯 DSL 解答的正确性。"""

from contextlib import redirect_stdout
import importlib.util
from io import StringIO
import json
import unittest
from unittest.mock import patch

from tools.runtime import ROOT, Runtime, build, catalog


class ArchiveTests(unittest.TestCase):
    def test_catalog_links_and_unique_ids(self):
        data = catalog()
        sources = json.loads((ROOT / "research" / "sources.json").read_text(encoding="utf-8"))
        source_ids = {item["id"] for item in sources["sources"]}
        problems = data["problems"]
        self.assertEqual(len({p["id"] for p in problems}), len(problems))
        self.assertEqual(len({c["id"] for c in data["candidates"]}), len(data["candidates"]))
        for entry in problems:
            with self.subTest(problem=entry["id"]):
                directory = ROOT / entry["directory"]
                self.assertTrue((directory / "README.md").is_file())
                self.assertTrue(set(entry["sources"]) <= source_ids)
                self.assertTrue(set(entry["dependencies"]) <= {p["id"] for p in problems if p["phase"] <= entry["phase"]})
                if entry["status"] == "solved":
                    self.assertTrue((directory / "solution.pp3").is_file())
                    self.assertTrue((directory / "cases.json").is_file())
                else:
                    self.assertFalse((directory / "solution.pp3").exists())

    def test_sample_cases_for_all_solved_problems(self):
        for entry in catalog()["problems"]:
            if entry["status"] != "solved":
                continue
            directory = ROOT / entry["directory"]
            ir = build((directory / "solution.pp3").read_text(encoding="ascii"))
            cases = json.loads((directory / "cases.json").read_text(encoding="utf-8"))
            for case in cases:
                with self.subTest(problem=entry["id"], name=case["name"]):
                    output = StringIO()
                    with patch("sys.stdin", StringIO(case["stdin"])), redirect_stdout(output):
                        Runtime(can_direct_addressing=False).run(ir)
                    self.assertEqual(output.getvalue(), case["stdout"])

    def test_signed_add_small_exhaustive_range(self):
        ir = build((ROOT / "problems/P001-signed-add/solution.pp3").read_text(encoding="ascii"))
        for a in range(-12, 13):
            for b in range(-12, 13):
                with self.subTest(a=a, b=b):
                    output = StringIO()
                    with patch("sys.stdin", StringIO(f"{a}\n{b}\n")), redirect_stdout(output):
                        Runtime(can_direct_addressing=False).run(ir)
                    self.assertEqual(output.getvalue(), f"{a + b}\n")

    def test_generator_reproduces_archived_solution(self):
        directory = ROOT / "problems/P001-signed-add"
        spec = importlib.util.spec_from_file_location("signed_add_generator", directory / "generator.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.make_code(), (directory / "solution.pp3").read_text(encoding="ascii"))

    def test_direct_addressing_is_rejected(self):
        for code in ["#1", "$1", "%1", "&0 [ #1 ]"]:
            with self.subTest(code=code), self.assertRaises(ValueError):
                build(code)


if __name__ == "__main__":
    unittest.main()
