"""Build the sample curriculum the team develops against."""
from . import db

COURSE = [
    ("Foundations", ["What a candle says", "Reading a session", "Risk before entry"]),
    ("Structure", ["Swings and internals", "Break of structure", "The retest"]),
    ("Execution", ["Entry models", "Managing a runner"]),
]


def seed(conn):
    db.reset(conn)
    with conn.cursor() as cur:
        for s_index, (title, lessons) in enumerate(COURSE, start=1):
            cur.execute(
                "INSERT INTO sections (course_id, title, position) VALUES (1, %s, %s) RETURNING id",
                (title, s_index),
            )
            section_id = cur.fetchone()[0]
            for l_index, lesson in enumerate(lessons, start=1):
                cur.execute(
                    "INSERT INTO lessons (section_id, title, position, published) "
                    "VALUES (%s, %s, %s, true)",
                    (section_id, lesson, l_index),
                )
    conn.commit()


if __name__ == "__main__":
    conn = db.connect()
    seed(conn)
    print("seeded")
