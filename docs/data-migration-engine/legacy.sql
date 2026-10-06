-- SYNTHETIC legacy source: 1000 deterministic customers in legacy formats.
-- Rows where cust_no % 143 = 0 (6 rows: 143..858) have an invalid email on purpose.
CREATE TABLE customers (
  cust_no       integer PRIMARY KEY,
  full_name     text    NOT NULL,          -- "Last, First"
  email         text    NOT NULL,          -- mixed case, stray spaces
  signup        text    NOT NULL,          -- MM/DD/YYYY
  status_code   char(1) NOT NULL,          -- A / I / S
  balance_cents text    NOT NULL           -- integer cents as text
);
INSERT INTO customers
SELECT n,
       'Surname' || n || ', Given' || n,
       CASE WHEN n % 143 = 0 THEN ' user' || n || '.example.invalid '
            ELSE ' User' || n || '@Example.INVALID ' END,
       to_char(date '2019-01-01' + (n * 3), 'MM/DD/YYYY'),
       (ARRAY['A','I','S'])[1 + n % 3],
       ((n * 7919) % 500000)::text
FROM generate_series(1, 1000) AS n;
