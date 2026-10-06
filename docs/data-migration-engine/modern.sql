-- Target schema for the migration.
CREATE TABLE customers (
  id            integer PRIMARY KEY,
  first_name    text    NOT NULL,
  last_name     text    NOT NULL,
  email         text    NOT NULL UNIQUE,
  signed_up_on  date    NOT NULL,
  status        text    NOT NULL CHECK (status IN ('active','inactive','suspended')),
  balance       numeric(12,2) NOT NULL,
  migrated_from text    NOT NULL,
  migrated_at   timestamptz NOT NULL DEFAULT now()
);
