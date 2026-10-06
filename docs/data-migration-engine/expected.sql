-- Independent SQL statement of the intended transformation, used only by the
-- verifier to compare against what the pipeline actually wrote.
SELECT cust_no AS id,
       trim(split_part(full_name, ',', 2)) AS first_name,
       trim(split_part(full_name, ',', 1)) AS last_name,
       lower(trim(email)) AS email,
       to_date(signup, 'MM/DD/YYYY') AS signed_up_on,
       CASE status_code WHEN 'A' THEN 'active' WHEN 'I' THEN 'inactive' ELSE 'suspended' END AS status,
       (balance_cents::numeric / 100)::numeric(12,2) AS balance
FROM customers
WHERE position('@' IN email) > 0
