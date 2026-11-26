CREATE TABLE promotions (
  code            TEXT PRIMARY KEY,
  name            TEXT NOT NULL,
  percent         INTEGER NOT NULL CHECK (percent BETWEEN 1 AND 100),
  cuisine         TEXT,
  restaurant_city TEXT,
  customer_city   TEXT
);

INSERT INTO promotions (code, name, percent, cuisine, restaurant_city, customer_city) VALUES
  ('WELCOME5',    'Welcome discount',      5,  NULL,    NULL,        NULL),
  ('CZECH10',     'Czech cuisine week',    10, 'czech', NULL,        NULL),
  ('LOCAL15',     'Krecovice restaurants', 15, NULL,    'Krecovice', NULL),
  ('NEIGHBOUR20', 'Krecovice customers',   20, NULL,    NULL,        'Krecovice'),
  ('PRAGUE25',    'Prague restaurants',    25, NULL,    'Praha',     NULL);
