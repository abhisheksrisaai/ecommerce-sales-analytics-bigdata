#!/usr/bin/env python3
"""
BCSE402L - Big Data Analytics (TH)
DA-2 artefact: Hadoop Streaming MapReduce job #3 (reducer)

Input  (sorted by key, tab separated from mapper or combiner):
        payment_type    1    payment_value
     or payment_type    partial_count    partial_total
Output (tab separated):
        payment_type    count    total    average

Hadoop guarantees that all pairs sharing a key arrive at the same reducer in
contiguous, key-sorted order, so the reducer only needs to detect key changes.
Both the mapper and the combiner emit the same 3-column shape, which is what
makes it valid to use a combiner for this job at all.
"""
import sys

COL_COUNT = 1
COL_VALUE = 2


def emit(key, count, total):
    average = total / count if count else 0.0
    sys.stdout.write("{0}\t{1}\t{2:.2f}\t{3:.2f}\n".format(
        key, count, total, average))


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

        # Key change -> the previous group is complete, flush it.
        if current_key is not None and key != current_key:
            emit(current_key, count, total)
            count = 0
            total = 0.0

        current_key = key
        count += partial_count
        total += partial_value

    # Flush the final group.
    if current_key is not None:
        emit(current_key, count, total)


if __name__ == "__main__":
    main()
