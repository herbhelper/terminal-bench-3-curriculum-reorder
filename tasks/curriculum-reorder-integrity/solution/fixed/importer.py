"""Bulk import of lessons from the legacy export.

The export is a list of dicts. It is not uniform: older records carry only a
title, newer ones carry duration and publication state, and a handful carry
fields this schema does not have at all.

A record's columns are read from that record. Taking the column list from the
first record and then reading every later record against it does two things at
once: a field the first record lacks is dropped from every row that has it, and
a field the first record has but a later one lacks arrives as NULL instead of
falling back to the column default.
"""
from . import db

COLUMNS = ("title", "published", "duration_s")


def import_batch(conn, section_id, records):
    """Insert every record into one section, in the order given.

    Returns the list of new lesson ids.
    """
    if not records:
        return []

    tail = db.one(
        conn,
        "SELECT max(position) AS p FROM lessons WHERE section_id = %s",
        (section_id,),
    )
    position = (tail["p"] or 0) + 1

    ids = []
    with conn.cursor() as cur:
        for record in records:
            columns = [c for c in COLUMNS if c in record]
            values = [record[c] for c in columns]
            cur.execute(
                "INSERT INTO lessons (section_id, position{}{}) VALUES (%s, %s{}{}) RETURNING id".format(
                    ", " if columns else "",
                    ", ".join(columns),
                    ", " if columns else "",
                    ", ".join(["%s"] * len(columns)),
                ),
                [section_id, position] + values,
            )
            ids.append(cur.fetchone()[0])
            position += 1
    conn.commit()
    return ids
