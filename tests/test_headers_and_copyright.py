# pylint: disable=missing-module-docstring
# pylint: disable=missing-function-docstring
import os
import re
import datetime
import pprint
from pathlib import Path
import pytest


def test_header():
    skipfiles = {"__init__.py", "conftest.py", "setup.py"}
    skipdirs = {"docs", ".", "tests", "__pycache__", "venv"}
    failures = []
    quantify_path = Path(__file__).resolve().parent.parent.resolve()
    header_lines = [
        "# Repository: https://gitlab.com/quantify-os/quantify-scheduler",
        "# Licensed according to the LICENCE file on the master branch",
    ]
    for root, _, files in os.walk(quantify_path):
        # skip hidden folders, etc
        if any(part.startswith(name) for part in Path(root).parts for name in skipdirs):
            continue
        for file_name in files:
            if file_name[-3:] == ".py" and file_name not in skipfiles:
                file_path = Path(root) / file_name
                print(f"Processing header in: {file_path}")
                with open(file_path, "r") as file:
                    lines_iter = (line.strip() for line in file)
                    line_matches = [
                        expected_line == line
                        for expected_line, line in zip(header_lines, lines_iter)
                    ]
                    if not all(line_matches):
                        failures.append(str(file_path))
    if failures:
        pytest.fail("Bad headers:\n{}".format(pprint.pformat(failures)))


def test_docs_copyright():
    quantify_path = Path(__file__).resolve().parent.parent.resolve()
    conf_file = quantify_path / "docs" / "conf.py"
    copyright_found = False
    current_year = str(datetime.datetime.now().year)
    cr_match = 'copyright = "2020-20.*Qblox & Orange Quantum Systems'
    with open(conf_file, "r") as file:
        for line in file.readlines():
            if re.match(cr_match, line):
                if current_year in line:
                    copyright_found = True
                break

    assert copyright_found, (
        f"No correct copyright claim for {current_year} matching "
        f"`{cr_match}` in {str(conf_file)}."
    )
