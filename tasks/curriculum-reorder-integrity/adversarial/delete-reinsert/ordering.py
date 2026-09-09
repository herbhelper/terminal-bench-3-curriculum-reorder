"""ADVERSARIAL VARIANT — delete-reinsert

Wrong fix #3: rebuild the section instead of reordering it.

Deleting the section's lessons and writing them back in the intended order
sidesteps every intermediate state, and every assertion about ordering passes.
The lessons are new rows: their ids change, so progress records, bookmarks and
the audit trail now point at lessons that no longer exist.

Original docstring: placing lessons inside a section, and moving them between sections.

Order is dense and 1-based within a section: a section holding four lessons
uses positions 1, 2, 3, 4 with no gaps and no duplicates.

Every write here happens with `lessons_section_position_key` deferred to the
end of the transaction. A reorder has to pass through a state where two rows
briefly share a position, and deferring is the only way to allow that without
either dropping the constraint or parking rows at fake positions first — and
parking them would put rows in the audit trail that never really moved.
"""
from . import db

CONSTRAINT = "lessons_section_position_key"


def _defer(cur):
    cur.execute(f"SET CONSTRAINTS {CONSTRAINT} DEFERRED")


def lessons_in(conn, section_id):
    """Every lesson in one section, in curriculum order."""
    return db.rows(
        conn,
        "SELECT id, section_id, title, position FROM lessons "
        "WHERE section_id = %s ORDER BY position",
        (section_id,),
    )


def _count(conn, section_id):
    return db.one(
        conn, "SELECT count(*) AS n FROM lessons WHERE section_id = %s", (section_id,)
    )["n"]


def append_lesson(conn, section_id, title, duration_s=0):
    """Add a lesson to the end of a section and return its id.

    The end of *this* section: positions are per-section, and sections are not
    laid out contiguously across the table, so the table-wide maximum belongs
    to whichever section happens to be longest.
    """
    tail = db.one(
        conn,
        "SELECT max(position) AS p FROM lessons WHERE section_id = %s",
        (section_id,),
    )
    position = (tail["p"] or 0) + 1
    row = db.one(
        conn,
        "INSERT INTO lessons (section_id, title, position, duration_s) "
        "VALUES (%s, %s, %s, %s) RETURNING id",
        (section_id, title, position, duration_s),
    )
    conn.commit()
    return row["id"]


def move_lesson(conn, lesson_id, to_section_id, to_position):
    lesson = db.one(
        conn,
        "SELECT id, section_id, title, position, published, duration_s "
        "FROM lessons WHERE id = %s",
        (lesson_id,),
    )
    if lesson is None:
        raise LookupError(f"no lesson {lesson_id}")

    from_section = lesson["section_id"]
    source = [r for r in lessons_in(conn, from_section) if r["id"] != lesson_id]
    dest = source if to_section_id == from_section else lessons_in(conn, to_section_id)
    ids = [r["id"] for r in dest]
    ids.insert(min(int(to_position), len(ids) + 1) - 1, lesson_id)

    rows = {
        r["id"]: r
        for r in db.rows(
            conn,
            "SELECT id, title, published, duration_s FROM lessons WHERE id = ANY(%s)",
            (ids,),
        )
    }

    with conn.cursor() as cur:
        cur.execute("DELETE FROM lessons WHERE id = ANY(%s)", (ids,))
        for index, lid in enumerate(ids, start=1):
            row = rows[lid]
            cur.execute(
                "INSERT INTO lessons (section_id, title, position, published, duration_s) "
                "VALUES (%s, %s, %s, %s, %s)",
                (to_section_id, row["title"], index, row["published"], row["duration_s"]),
            )
        if to_section_id != from_section:
            for index, r in enumerate(source, start=1):
                cur.execute(
                    "UPDATE lessons SET position = %s WHERE id = %s", (index, r["id"])
                )
    conn.commit()


def normalize_positions(conn, section_id):
    """Rewrite a section's positions as a dense 1..N run, order preserved.

    One statement, so no row is written twice and the audit trail stays a
    record of lessons that moved rather than of the renumbering itself.
    """
    with conn.cursor() as cur:
        _defer(cur)
        cur.execute(
            """
            WITH ordered AS (
                SELECT id, row_number() OVER (ORDER BY position, id) AS rn
                  FROM lessons
                 WHERE section_id = %s
            )
            UPDATE lessons l
               SET position = ordered.rn
              FROM ordered
             WHERE l.id = ordered.id
               AND l.position IS DISTINCT FROM ordered.rn
            """,
            (section_id,),
        )
    conn.commit()
