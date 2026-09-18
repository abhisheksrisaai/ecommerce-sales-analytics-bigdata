#!/usr/bin/env python3
"""
BCSE402L - Big Data Analytics (TH)
DA-2 artefact: Hadoop Streaming MapReduce job #3 (combiner)

Why a separate script from the reducer?
    A combiner must be a function that is *semantically equivalent to the
    reducer at the partial-aggregation level*, and it must consume exactly
    what the mapper emits and emit something the reducer can consume. An
    early version of this job reused the reducer as the combiner, which
    emitted a 4-column record (type, count, total, average); the reducer
    then expected 3 columns and silently discarded every combined record,
    producing an empty output directory. The combiner is therefore kept
    separate and emits the same 3-column shape the reducer expects.

Input  (mapper output, tab separated):  payment_type    1    payment_value
Output (tab separated)               :  payment_type    partial_count    partial_total
"""
import sys

COL_COUNT = 1
COL_VALUE = 2


def main():
    current_key = None
    count = 0
    total = 0.0

    for raw_line in sys.stdin:
        line = raw_line.rstrip("\n")
        if not line:
            continue

        fields = line.split("\t")
        if len(fields) != 3:
            continue

        key = fields[0]
        try:
            partial_count = int(fields[COL_COUNT])
            partial_value = float(fields[COL_VALUE])
        except ValueError:
            continue

        if current_key is not None and key != current_key:
            # Same 3-column contract as the mapper, so the reducer can read it.
            sys.stdout.write("{0}\t{1}\t{2}\n".format(current_key, count, total))
            count = 0
            total = 0.0

        current_key = key
        count += partial_count
        total += partial_value

    if current_key is not None:
        sys.stdout.write("{0}\t{1}\t{2}\n".format(current_key, count, total))


if __name__ == "__main__":
    main()
