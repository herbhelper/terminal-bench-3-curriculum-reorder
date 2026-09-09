"""Placing lessons inside a section, and moving them between sections.

Order is dense and 1-based within a section: a section holding four lessons
uses positions 1, 2, 3, 4 with no gaps and no duplicates.
"""
from . import db


def lessons_in(conn, section_id):
    """Every lesson in one section, in curriculum order."""
    return db.rows(
        conn,
        "SELECT id, section_id, title, position FROM lessons "
        "WHERE section_id = %s ORDER BY position",
        (section_id,),
    )


def append_lesson(conn, section_id, title, duration_s=0):
    """Add a lesson to the end of a section and return its id."""
    tail = db.one(conn, "SELECT max(position) AS p FROM lessons")
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
    """Move one lesson to a given position, inside its section or into another.

    Positions in the section it leaves close up behind it; positions in the
    section it enters open up to receive it.
    """
    lesson = db.one(
        conn, "SELECT id, section_id, position FROM lessons WHERE id = %s", (lesson_id,)
    )
    if lesson is None:
        raise LookupError(f"no lesson {lesson_id}")

    with conn.cursor() as cur:
        # Close the hole the lesson leaves behind.
        cur.execute(
            "UPDATE lessons SET position = position - 1 "
            "WHERE section_id = %s AND position > %s",
            (lesson["section_id"], lesson["position"]),
        )
        # Open a hole at the destination.
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
    """Rewrite a section's positions as a dense 1..N run, order preserved."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM lessons WHERE section_id = %s ORDER BY position, id",
            (section_id,),
        )
        for index, (lesson_id,) in enumerate(cur.fetchall(), start=1):
            cur.execute(
                "UPDATE lessons SET position = %s WHERE id = %s", (index, lesson_id)
            )
    conn.commit()
