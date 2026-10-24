"""README claims audit.

docs/claims.md lists every number in README.md with its source file and a selector:
- CSV: `<filters> -> <value>`. Filters are `column=value` pairs joined by "; " (also !=, >=, <=,
  >, <; `*` for all rows). The value is a column (exactly one row), or mean/min/max/sum(expr),
  count(), or expr(expr) on one row; expr is a pandas expression over the columns.
- JSON: `key a.b` (list items as a.0).
- Markdown table: `md <column>=<value> -> <column>`, over every table in the file.
- Text: `contains <text>`: the source contains the text, and the claim is part of it.
Formats are Python format specs, or `x100:<spec>` (scaled by 100), `time:<strftime>` (an ISO
timestamp), `str` and `text`.
"""

import json
import math
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from src.config import PROJECT_ROOT

README = PROJECT_ROOT / "README.md"
CLAIMS = PROJECT_ROOT / "docs" / "claims.md"
ALLOWED_SOURCE_DIRS = ("reports/", "config/")
FILTER = re.compile(r"^(\w+)\s*(>=|<=|!=|=|<|>)\s*(.+)$")
AGGREGATE = re.compile(r"^(mean|min|max|sum|count|expr)\((.*)\)$")
PERCENT = re.compile(r"[-+]?\d+(?:\.\d+)?%")
DECIMAL = re.compile(r"[-+]?\d+\.\d+")
FORBIDDEN = ("closing odds", "beats the bookmaker", "outperforms")
PROSE_PERCENT_ALLOWED = {"58%"}  # the tripwire threshold, a rule rather than an accuracy figure
PROVENANCE_SENTENCE = (
    "The first {first_batch_predictions} predictions were logged at {first_logged} from the working tree, "
    "the code was committed as {code_commit} at {committed}, both before the first kickoff ({first_kickoff}), "
    "and recomputing the {recompute_fixtures} predictions from the committed code reproduces them exactly "
    "(max difference {recompute_max_abs_difference})."
)


# ---------- evaluation ----------

def apply_filters(frame: pd.DataFrame, filters: str) -> pd.DataFrame:
    if filters.strip() == "*":
        return frame
    for part in filters.split("; "):
        column, operator, value = FILTER.match(part.strip()).groups()
        values = frame[column].astype(str)
        test = {"=": values == value, "!=": values != value, ">=": values >= value,
                "<=": values <= value, ">": values > value, "<": values < value}[operator]
        frame = frame[test]
    return frame


def csv_value(path: Path, selector: str) -> object:
    filters, value = (part.strip() for part in selector.split("->"))
    rows = apply_filters(pd.read_csv(path), filters)
    aggregate = AGGREGATE.match(value)
    if aggregate is None:
        if len(rows) != 1:
            raise ValueError(f"{selector!r} matched {len(rows)} rows in {path.name}")
        return rows[value].iloc[0]
    function, expression = aggregate.groups()
    if function == "count":
        return len(rows)
    values = rows.eval(expression) if expression else rows
    if function == "expr":
        if len(rows) != 1:
            raise ValueError(f"{selector!r} matched {len(rows)} rows in {path.name}")
        return values.iloc[0]
    return getattr(values, function)()


def json_value(path: Path, key: str) -> object:
    value = json.loads(path.read_text(encoding="utf-8"))
    for part in key.split("."):
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def markdown_tables(text: str) -> list[pd.DataFrame]:
    tables, block = [], []
    for line in text.splitlines() + [""]:
        if line.startswith("|"):
            block.append([cell.strip() for cell in line.strip().strip("|").split("|")])
        elif block:
            header, *body = [row for row in block if not set("".join(row)) <= set("-: ")]
            tables.append(pd.DataFrame(body, columns=header))
            block = []
    return tables


def markdown_value(path: Path, selector: str) -> str:
    key, column = (part.strip() for part in selector.split("->"))
    key_column, key_value = key.split("=", 1)
    for table in markdown_tables(path.read_text(encoding="utf-8")):
        if key_column in table and column in table:
            rows = table[table[key_column] == key_value]
            if len(rows) == 1:
                return rows[column].iloc[0]
    raise ValueError(f"{selector!r} not found in {path.name}")


def evaluate(source: str, selector: str) -> object:
    path = PROJECT_ROOT / source
    if selector.startswith("contains "):
        return selector.removeprefix("contains ") if selector.removeprefix("contains ") in path.read_text(
            encoding="utf-8") else None
    if selector.startswith("key "):
        return json_value(path, selector.removeprefix("key "))
    if selector.startswith("md "):
        return markdown_value(path, selector.removeprefix("md "))
    return csv_value(path, selector)


def render(value: object, form: str) -> str:
    if form in ("str", "text"):
        return str(value)
    if form.startswith("time:"):
        return datetime.fromisoformat(str(value)).astimezone(timezone.utc).strftime(form.removeprefix("time:"))
    scale = 1.0
    if form.startswith("x100:"):
        scale, form = 100.0, form.removeprefix("x100:")
    if form.endswith("d"):
        number = float(value)
        if not number.is_integer():
            raise ValueError(f"{value!r} is not a whole number")
        return format(int(number), form)
    return format(float(value) * scale, form)


def claim_rows() -> list[dict[str, str]]:
    """Rows of the claims table in docs/claims.md."""
    rows = []
    for line in CLAIMS.read_text(encoding="utf-8").splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if line.startswith("|") and len(cells) == 5 and cells[0].isdigit():
            number, claim, source, selector, form = cells
            rows.append({"number": number, "claim": claim.strip("`"), "source": source.strip("`"),
                         "selector": selector.strip("`"), "format": form.strip("`")})
    return rows


# ---------- README text helpers ----------

def without_code_and_findings(text: str) -> str:
    text = text.split("\n## Findings")[0]
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    return re.sub(r"`[^`]*`", "", text)


def prose(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.startswith("|"))


def table_blocks(text: str) -> list[str]:
    blocks, block = [], []
    for line in text.splitlines() + [""]:
        if line.startswith("|"):
            block.append(line)
        elif block:
            blocks.append("\n".join(block))
            block = []
    return blocks


needs_docs = pytest.mark.skipif(not (README.exists() and CLAIMS.exists()), reason="README.md or docs/claims.md missing")


@needs_docs
def test_every_claim_equals_its_source_after_the_same_rounding():
    rows = claim_rows()
    assert rows, "docs/claims.md lists no claims"
    wrong = []
    for row in rows:
        value = evaluate(row["source"], row["selector"])
        rendered = None if value is None else render(value, row["format"])
        ok = (row["claim"] in rendered) if row["format"] == "text" and rendered else rendered == row["claim"]
        if not ok:
            wrong.append((row["number"], row["claim"], rendered))
    assert wrong == []


@needs_docs
def test_claim_sources_are_reports_or_config_except_the_listed_rule_sources():
    sources = {row["source"] for row in claim_rows()}
    outside = sorted(source for source in sources if not source.startswith(ALLOWED_SOURCE_DIRS))
    assert outside == ["CLAUDE.md"]  # clause number and rule thresholds, listed as exceptions in docs/claims.md


def producers() -> dict[str, str]:
    """Source file -> the command that produces it, from the sources table in docs/claims.md."""
    rows = {}
    for line in CLAIMS.read_text(encoding="utf-8").splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if line.startswith("| `") and len(cells) == 2:
            rows[cells[0].strip("`")] = cells[1]
    return rows


@needs_docs
def test_every_claim_source_names_the_command_that_produces_it():
    commands = producers()
    assert {row["source"] for row in claim_rows()} <= set(commands)
    for source, command in commands.items():
        for module in re.findall(r"scripts\.(\w+)", command):
            assert (PROJECT_ROOT / "scripts" / f"{module}.py").exists(), (source, module)
    assert "scripts.make_planted_leak_report" in commands["reports/planted_leaks.csv"]
    assert "scripts.make_forward_provenance" in commands["reports/forward_provenance.json"]


@needs_docs
def test_every_percentage_and_decimal_in_the_readme_is_claimed():
    claimed = {row["claim"] for row in claim_rows()}
    text = without_code_and_findings(README.read_text(encoding="utf-8"))
    percentages = PERCENT.findall(text)
    decimals = DECIMAL.findall(PERCENT.sub(" ", text))
    missing = sorted({token for token in percentages + decimals if token not in claimed})
    assert missing == []


@needs_docs
def test_no_forbidden_phrases_and_no_headline_accuracy_outside_a_bookmaker_table():
    raw = README.read_text(encoding="utf-8")
    assert [phrase for phrase in FORBIDDEN if phrase in raw.lower()] == []
    text = without_code_and_findings(raw)
    assert set(PERCENT.findall(prose(text))) <= PROSE_PERCENT_ALLOWED
    for block in table_blocks(text):
        if PERCENT.search(block):
            assert "bookmaker" in block.lower() and "matches" in block.lower(), block.splitlines()[0]


@needs_docs
def test_findings_section_is_left_for_the_author():
    assert "## Findings\n\n(to be written by the author)" in README.read_text(encoding="utf-8")


def provenance() -> dict:
    return json.loads((PROJECT_ROOT / "reports" / "forward_provenance.json").read_text(encoding="utf-8"))


@needs_docs
def test_provenance_sentence_is_filled_from_the_provenance_record():
    record = provenance()
    sentence = PROVENANCE_SENTENCE.format(
        first_batch_predictions=record["first_batch_predictions"],
        first_logged=render(record["first_logged_at_utc"], "time:%Y-%m-%d %H:%M:%SZ"),
        code_commit=record["code_commit"], committed=render(record["code_committed_at_utc"], "time:%H:%M:%SZ"),
        first_kickoff=render(record["first_kickoff_utc"], "time:%H:%MZ"),
        recompute_fixtures=record["recompute_fixtures"],
        recompute_max_abs_difference=record["recompute_max_abs_difference"])
    assert sentence in README.read_text(encoding="utf-8")


@pytest.mark.skipif(subprocess.run(["git", "--version"], capture_output=True).returncode != 0, reason="git missing")
def test_provenance_record_agrees_with_the_log_and_git():
    record = provenance()
    log = pd.read_csv(PROJECT_ROOT / "data" / "forward" / "predictions_log.csv")
    first = log[log["predicted_at"] == log["predicted_at"].min()]
    assert record["first_logged_at_utc"] == pd.Timestamp(log["predicted_at"].min()).isoformat()
    assert record["first_batch_predictions"] == len(first)
    assert record["first_kickoff_utc"] == pd.to_datetime(first["kickoff"], utc=True).min().isoformat()
    assert record["logged_git_commit"] == first["git_commit"].iloc[0]
    committed = subprocess.run(["git", "log", "-1", "--format=%cI", record["code_commit"]], cwd=PROJECT_ROOT,
                               capture_output=True, text=True, check=True).stdout.strip()
    assert record["code_committed_at_utc"] == datetime.fromisoformat(committed).astimezone(timezone.utc).isoformat()
    assert record["first_logged_at_utc"] < record["code_committed_at_utc"] < record["first_kickoff_utc"]
    assert math.isclose(record["recompute_max_abs_difference"], 0.0) and record["recompute_inputs_unchanged"]
