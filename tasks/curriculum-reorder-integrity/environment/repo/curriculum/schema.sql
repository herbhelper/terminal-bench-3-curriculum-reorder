-- Curriculum service schema.
--
-- A course is a list of sections; a section is an ordered list of lessons.
-- Lesson order inside a section is dense and 1-based, and the database is the
-- thing that enforces it: no two lessons in one section may share a position.
--
-- The uniqueness constraint is DEFERRABLE so that a legitimate reorder can
-- pass through intermediate states inside one transaction. It is INITIALLY
-- IMMEDIATE so that ordinary single-row writes still fail fast.

CREATE TABLE sections (
    id         serial PRIMARY KEY,
    course_id  integer NOT NULL,
    title      text    NOT NULL,
    position   integer NOT NULL
);

CREATE TABLE lessons (
    id          serial PRIMARY KEY,
    section_id  integer NOT NULL REFERENCES sections (id) ON DELETE CASCADE,
    title       text    NOT NULL,
    position    integer NOT NULL,
    published   boolean NOT NULL DEFAULT false,
    duration_s  integer NOT NULL DEFAULT 0
);

ALTER TABLE lessons
    ADD CONSTRAINT lessons_section_position_key
    UNIQUE (section_id, position)
    DEFERRABLE INITIALLY IMMEDIATE;

-- Every change to a lesson's place in the curriculum is recorded. Support
-- reads this table to answer "who moved this lesson, and from where".
CREATE TABLE lesson_moves (
    id            bigserial PRIMARY KEY,
    lesson_id     integer NOT NULL,
    from_section  integer NOT NULL,
    from_position integer NOT NULL,
    to_section    integer NOT NULL,
    to_position   integer NOT NULL,
    moved_at      timestamptz NOT NULL DEFAULT now()
);

CREATE FUNCTION log_lesson_move() RETURNS trigger AS $$
BEGIN
    INSERT INTO lesson_moves (lesson_id, from_section, from_position, to_section, to_position)
    VALUES (OLD.id, OLD.section_id, OLD.position, NEW.section_id, NEW.position);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER lessons_log_move
    AFTER UPDATE ON lessons
    FOR EACH ROW
    WHEN (OLD.position IS DISTINCT FROM NEW.position
          OR OLD.section_id IS DISTINCT FROM NEW.section_id)
    EXECUTE FUNCTION log_lesson_move();
