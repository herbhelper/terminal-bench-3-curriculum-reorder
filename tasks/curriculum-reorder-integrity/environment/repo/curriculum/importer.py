"""Bulk import of lessons from the legacy export.

The export is a list of dicts. It is not uniform: older records carry only a
title, newer ones carry duration and publication state, and a handful carry
fields this schema does not have at all.
"""
from . import db, ordering

COLUMNS = {"title", "published", "duration_s"}


def import_batch(conn, section_id, records):
    """Insert every record into one section, in the order given.

    Returns the list of new lesson ids.
    """
    if not records:
        return []

    columns = [c for c in records[0] if c in COLUMNS]
    ids = []
    with conn.cursor() as cur:
        for record in records:
            values = [record.get(c) for c in columns]
            tail = db.one(conn, "SELECT max(position) AS p FROM lessons")
            position = (tail["p"] or 0) + 1
            cur.execute(
                "INSERT INTO lessons (section_id, position, {}) VALUES ({}) RETURNING id".format(
                    ", ".join(columns), ", ".join(["%s"] * (len(columns) + 2))
                ),
                [section_id, position] + values,
            )
            ids.append(cur.fetchone()[0])
    conn.commit()
    return ids
