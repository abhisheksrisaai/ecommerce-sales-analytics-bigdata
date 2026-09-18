#!/usr/bin/env python3
"""
BCSE402L - Big Data Analytics (TH)
DA-2 artefact: CSV normalisation for the clean landing layer.

Problem
    The Olist files are not uniformly well-formed as far as a line-oriented
    reader is concerned:
      * quoting is inconsistent between files, and even between the header and
        the data rows of a single file (some rows quote every field, others
        quote only the identifier fields, and some quote nothing);
      * olist_order_reviews_dataset.csv embeds newlines inside quoted free-text
        comment fields.
    Hive reads one line per record, so an embedded newline breaks the record
    and the serde aborts the query with
      SerDeException: CsvMalformedLineException: Unterminated quoted field at
      end of CSV line.
    That failure is data-dependent, so it hit only the two queries that read the
    reviews table while every other query succeeded.

Fix
    Re-serialise each file with a real CSV parser, dropping the header row and
    normalising three things that break a line-oriented, escapeChar-configured
    reader:
      * a newline inside a field becomes a space, because Hive reads one line
        per record and a multi-line quoted value otherwise fails with
        CsvMalformedLineException;
      * a double quote inside a field becomes a single quote, because the serde
        is configured with an explicit escapeChar, which makes OpenCSV read a
        backslash as the escape mechanism rather than RFC 4180 quote doubling;
      * a backslash inside a field becomes a forward slash, because under that
        same escapeChar rule a field ending :\\" escapes its own closing quote.
        Exactly one row in olist_order_reviews_dataset.csv does this, and it
        was sufficient to fail every query that read the reviews table.

    Field values, column order and record count are otherwise preserved, so the
    clean layer is a faithful, line-safe rendering of the raw layer.

Usage:  python3 csv_normalize.py <input.csv> > <output.csv>
"""
import csv
import sys


def sanitize(field):
    """Make a field safe for the line-oriented, escapeChar-configured serde.

    A backslash is replaced because the serde is configured with
    escapeChar='\\\\', so OpenCSV treats a backslash as escaping the character
    after it. One review comment in the source data contains the sequence
    :\\" immediately before the field's closing quote, which makes OpenCSV read
    the quote as escaped, leave the field open, and fail the whole query with
    'Unterminated quoted field at end of CSV line'. Replacing the backslash
    removes the interaction; no analytical column depends on it.
    """
    return (field
            .replace("\r\n", " ")
            .replace("\n", " ")
            .replace("\r", " ")
            .replace('"', "'")
            .replace("\\", "/"))


def main():
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2

    path = sys.argv[1]
    # newline="" lets the csv module handle the file's own line endings, and
    # quoting=QUOTE_MINIMAL reproduces standard CSV on output.
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        writer = csv.writer(sys.stdout, lineterminator="\n",
                            quoting=csv.QUOTE_MINIMAL)

        for index, row in enumerate(reader):
            if index == 0:
                continue                      # drop the header line
            writer.writerow([sanitize(field) for field in row])

    return 0


if __name__ == "__main__":
    sys.exit(main())
