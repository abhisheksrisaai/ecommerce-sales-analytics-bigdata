#!/usr/bin/env python3
"""
BCSE402L - Big Data Analytics (TH)
DA-2 artefact: Hadoop Streaming MapReduce job #3 (mapper)

Job    : Payment-type distribution - transaction count, total value and
         average value per payment method.
Shows  : the streaming interface itself (stdin -> stdout, tab separated),
         plus cleaning (header skip, malformed row drop, numeric validation).

Input  (CSV, header row):
    order_id,payment_sequential,payment_type,payment_installments,payment_value
Output (tab separated, one record per payment type):
    payment_type    1    payment_value
"""
import sys

EXPECTED_FIELDS = 5

# Positions in the source schema.
COL_ORDER_ID = 0
COL_PAYMENT_TYPE = 2
COL_PAYMENT_VALUE = 4


def unquote(field):
    """The header row quotes every column while data rows quote selectively
    (and in this file the payment columns are not quoted at all). Stripping
    surrounding quotes makes header detection and grouping consistent, and
    mirrors the helper used by the Java mappers."""
    t = field.strip()
    if len(t) >= 2 and t[0] == '"' and t[-1] == '"':
        return t[1:-1].strip()
    return t


def main():
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue

        fields = line.split(",")
        if len(fields) < EXPECTED_FIELDS:
            continue

        # Cleaning 1: skip the header. It is detected on the parsed value so
        # that a quoted header ("order_id",...) is recognised too.
        if unquote(fields[COL_ORDER_ID]) == "order_id":
            continue

        payment_type = unquote(fields[COL_PAYMENT_TYPE]) or "unknown"

        # Cleaning 2: the value column must be numeric; otherwise drop the row.
        try:
            value = float(unquote(fields[COL_PAYMENT_VALUE]))
        except ValueError:
            continue

        if value < 0:
            continue

        # Emit (key, value). The "1" carries the per-record count so the
        # combiner and reducer can compute count and sum in a single pass.
        sys.stdout.write("{0}\t1\t{1}\n".format(payment_type, value))


if __name__ == "__main__":
    main()
