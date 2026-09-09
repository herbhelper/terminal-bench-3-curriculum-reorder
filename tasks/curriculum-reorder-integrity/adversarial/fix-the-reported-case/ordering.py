"""ADVERSARIAL VARIANT — fix-the-reported-case

Wrong fix #4: fix exactly what the ticket described.

The report says dragging a lesson down inside its section fails, so this
rewrites the same-section path as a single UPDATE — which is correct, and which
passes because a DEFERRABLE INITIALLY IMMEDIATE constraint is checked at the end
of the statement rather than per row. The cross-section path is left as it was.
It is still two statements, and the first of them still lands on a duplicate.

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
        conn, "SELECT id, section_id, position FROM lessons WHERE id = %s", (lesson_id,)
    )
    if lesson is None:
        raise LookupError(f"no lesson {lesson_id}")

    from_section, from_position = lesson["section_id"], lesson["position"]

    if to_section_id == from_section:
        ceiling = max(_count(conn, from_section), 1)
        to_position = max(1, min(int(to_position), ceiling))
        if to_position == from_position:
            conn.rollback()
            return
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE lessons SET position = CASE
                    WHEN id = %(id)s THEN %(to)s
                    WHEN %(to)s < %(from)s AND position >= %(to)s AND position < %(from)s
                        THEN position + 1
                    WHEN %(to)s > %(from)s AND position > %(from)s AND position <= %(to)s
                        THEN position - 1
                    ELSE position END
                 WHERE section_id = %(section)s
                """,
                {"id": lesson_id, "to": to_position, "from": from_position,
                 "section": from_section},
            )
        conn.commit()
        return

    with conn.cursor() as cur:
        cur.execute(
            "UPDATE lessons SET position = position - 1 "
            "WHERE section_id = %s AND position > %s",
            (from_section, from_position),
        )
        cur.execute(
            "UPDATE lessons SET position = position + 1 "
            "WHERE section_id = %s AND position >= %s",
            (to_section_id, to_position),
        )
        cur.execute(
            "UPDATE lessons SET section_id = %s, position = %s WHERE id = %s",
            (to_section_id, to_position, lesson_id),
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
