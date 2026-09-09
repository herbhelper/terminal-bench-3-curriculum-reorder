"""ADVERSARIAL VARIANT — negative-parking

Wrong fix #2: park the rows at negative positions first.

This is the workaround the internet gives you for a unique ordering column, and
it is correct about ordering in every case in the bug report — up, down and
across sections all land dense and in the right order. It writes each affected
row twice, though: once out to a placeholder, once back to its real position.
The audit trail then holds two moves for every lesson in the section, including
lessons that finished exactly where they started.

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


def _plan(conn, lesson_id, from_section, to_section_id, to_position):
    """The id order each affected section should end up in."""
    if to_section_id == from_section:
        ids = [r["id"] for r in lessons_in(conn, from_section) if r["id"] != lesson_id]
        ids.insert(max(1, min(int(to_position), len(ids) + 1)) - 1, lesson_id)
        return [(from_section, ids)]

    source = [r["id"] for r in lessons_in(conn, from_section) if r["id"] != lesson_id]
    dest = [r["id"] for r in lessons_in(conn, to_section_id)]
    dest.insert(max(1, min(int(to_position), len(dest) + 1)) - 1, lesson_id)
    return [(from_section, source), (to_section_id, dest)]


def move_lesson(conn, lesson_id, to_section_id, to_position):
    lesson = db.one(
        conn, "SELECT id, section_id, position FROM lessons WHERE id = %s", (lesson_id,)
    )
    if lesson is None:
        raise LookupError(f"no lesson {lesson_id}")

    groups = _plan(conn, lesson_id, lesson["section_id"], to_section_id, to_position)

    with conn.cursor() as cur:
        parked = 0
        for _, ids in groups:
            for lid in ids:
                parked += 1
                cur.execute(
                    "UPDATE lessons SET position = %s WHERE id = %s", (-parked, lid)
                )
        for section, ids in groups:
            for index, lid in enumerate(ids, start=1):
                cur.execute(
                    "UPDATE lessons SET section_id = %s, position = %s WHERE id = %s",
                    (section, index, lid),
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
