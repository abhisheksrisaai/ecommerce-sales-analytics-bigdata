#!/usr/bin/env python3
"""
BCSE402L - Big Data Analytics (TH)
DA-2 artefact: Hive/HQL script driver.

Why this exists
    Hive 4 replaced the old CLI with Beeline. In this environment Beeline's
    script mode (`beeline -f file.hql`) is unreliable: its interactive prompt
    redraws overwrite the script lines being read, so statements reach the
    parser corrupted (e.g. "ROW FORMAT SERDE" arrives as "ROW FORMAROW
    FORMAT" and fails with
        ParseException ... near 'ROW' 'FORMAROW' 'FORMAROW').
    The same statements execute correctly when passed one at a time with
    `-e`. This driver therefore splits the .hql file into statements and runs
    each one through `beeline -e`, which also makes the per-query output
    self-attributing for the report.

Usage:
    python3 code/scripts/hive_exec.py code/hive/01_warehouse.hql
    python3 code/scripts/hive_exec.py code/hive/02_analytics.hql logs/hive_02.log
"""
import os
import re
import subprocess
import sys

BEELINE = "beeline"
URL = "jdbc:hive2://"
EXTRA = [
    "--hiveconf", "hive.cli.print.header=true",
    "--hiveconf", "hive.exec.dynamic.partition=true",
    "--hiveconf", "hive.exec.dynamic.partition.mode=nonstrict",
    "--hiveconf", "hive.exec.max.dynamic.partitions=2000",
    "--hiveconf", "hive.exec.max.dynamic.partitions.pernode=500",
]

NOISE = re.compile(r"^(SLF4J|log4j|Picked up|WARNING:|Hive Session ID|Connecting to|"
                   r"Connected to:|Driver:|Transaction isolation:|Beeline version|"
                   r"Closing:|^\s*$)")


def split_statements(text):
    """Strip `--` comments and split on top-level semicolons in one pass.

    Quote handling is escape-aware. The naive version of this function only
    toggled a boolean on every quote character and did not understand the
    backslash escapes used by Hive serde properties such as
        "quoteChar" = "\\""
    That left the scanner believing it was still inside a string literal, so
    later semicolons were treated as string content and whole statements were
    merged or lost. Quotes and comments are therefore resolved together here,
    with a backslash escaping the following character inside either quote
    style, exactly as Hive parses them.
    """
    statements = []
    buf = []
    in_single = False
    in_double = False
    escaped = False
    i = 0
    n = len(text)

    while i < n:
        ch = text[i]

        if escaped:
            escaped = False
            buf.append(ch)
            i += 1
            continue

        if in_single or in_double:
            if ch == "\\":
                escaped = True
            elif ch == "'" and in_single:
                in_single = False
            elif ch == '"' and in_double:
                in_double = False
            buf.append(ch)
            i += 1
            continue

        # Outside any literal: comments and delimiters are meaningful.
        if ch == "-" and text[i:i + 2] == "--":
            while i < n and text[i] != "\n":
                i += 1
            continue
        if ch == "'":
            in_single = True
            buf.append(ch)
        elif ch == '"':
            in_double = True
            buf.append(ch)
        elif ch == ";":
            stmt = "".join(buf).strip()
            if stmt:
                statements.append(stmt)
            buf = []
        else:
            buf.append(ch)
        i += 1

    tail = "".join(buf).strip()
    if tail:
        statements.append(tail)
    return statements


def run(statement, database=None):
    # Each invocation is a separate session, so a `USE <db>` statement would
    # not carry over to the next one. The database is therefore bound into the
    # connection URL instead, which is what makes multi-statement scripts work
    # when they are executed one statement at a time.
    url = "jdbc:hive2:///{0}".format(database) if database else URL
    cmd = [BEELINE, "--silent=true", "-u", url] + EXTRA + ["-e", statement]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    lines = [ln for ln in (proc.stdout + proc.stderr).splitlines()
             if not NOISE.match(ln) and "ShutdownHookManager" not in ln]
    return proc.returncode, lines


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2

    script_path = sys.argv[1]
    log_path = sys.argv[2] if len(sys.argv) > 2 else None

    with open(script_path) as fh:
        raw = fh.read()

    statements = split_statements(raw)
    total = len(statements)
    print("### {0} -> {1} statements".format(script_path, total))
    print()

    sink = open(log_path, "w") if log_path else None
    failures = 0
    database = None

    for i, stmt in enumerate(statements, 1):
        preview = " ".join(stmt.split())[:110]

        # `USE` is tracked as session state rather than executed on its own.
        use = re.match(r"^\s*USE\s+([A-Za-z_][\w]*)\s*$", stmt, re.IGNORECASE)
        if use:
            database = use.group(1)
            header = "=== [{0}/{1}] (session database -> {2})".format(i, total, database)
            print(header)
            if sink:
                sink.write(header + "\n\n")
            continue

        header = "=== [{0}/{1}] {2}".format(i, total, preview)
        print(header)
        if sink:
            sink.write(header + "\n")

        rc, lines = run(stmt, database)
        body = "\n".join(lines) if lines else "(no output)"
        print(body)
        print()
        if sink:
            sink.write(body + "\n\n")

        if rc != 0 or any(ln.startswith("Error:") for ln in lines):
            failures += 1
            print("!!! statement {0} reported an error (rc={1})".format(i, rc))
            if sink:
                sink.write("!!! statement {0} reported an error (rc={1})\n\n".format(i, rc))

    if sink:
        sink.close()
        print("log written to {0}".format(log_path))

    print("### {0}/{1} statements completed, {2} with errors".format(
        total - failures, total, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
