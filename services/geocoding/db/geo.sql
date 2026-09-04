CREATE TABLE addresses (
  street          TEXT NOT NULL,
  building_number TEXT NOT NULL,
  city            TEXT NOT NULL,
  postal_code     TEXT NOT NULL,
  lat             REAL NOT NULL,
  lon             REAL NOT NULL
);

CREATE INDEX idx_addresses_lookup ON addresses (city, street, building_number);

INSERT INTO addresses (street, building_number, city, postal_code, lat, lon) VALUES
  ('Hlavni',    '1',  'Krecovice', '25756', 49.7150, 14.4620),
  ('Hlavni',    '3',  'Krecovice', '25756', 49.7150, 14.4625),
  ('Hlavni',    '5',  'Krecovice', '25756', 49.7151, 14.4630),
  ('Hlavni',    '7',  'Krecovice', '25756', 49.7151, 14.4635),
  ('Skolni',    '2',  'Krecovice', '25756', 49.7175, 14.4660),
  ('Skolni',    '4',  'Krecovice', '25756', 49.7175, 14.4665),
  ('Skolni',    '6',  'Krecovice', '25756', 49.7176, 14.4670),
  ('Skolni',    '8',  'Krecovice', '25756', 49.7176, 14.4675),
  ('Kostelni',  '1',  'Krecovice', '25756', 49.7200, 14.4700),
  ('Kostelni',  '2',  'Krecovice', '25756', 49.7200, 14.4705),
  ('Kostelni',  '3',  'Krecovice', '25756', 49.7201, 14.4710),
  ('Kostelni',  '4',  'Krecovice', '25756', 49.7201, 14.4715),
  ('Zahradni',  '10', 'Krecovice', '25756', 49.7140, 14.4700),
  ('Zahradni',  '12', 'Krecovice', '25756', 49.7140, 14.4705),
  ('Zahradni',  '14', 'Krecovice', '25756', 49.7141, 14.4710),
  ('Zahradni',  '16', 'Krecovice', '25756', 49.7141, 14.4715),
  ('Polni',     '5',  'Krecovice', '25756', 49.7215, 14.4620),
  ('Polni',     '7',  'Krecovice', '25756', 49.7215, 14.4625),
  ('Polni',     '9',  'Krecovice', '25756', 49.7216, 14.4630),
  ('Polni',     '11', 'Krecovice', '25756', 49.7216, 14.4635),
  ('Nadrazni',  '21', 'Krecovice', '25756', 49.7125, 14.4655),
  ('Nadrazni',  '23', 'Krecovice', '25756', 49.7125, 14.4660),
  ('Nadrazni',  '25', 'Krecovice', '25756', 49.7126, 14.4665),
  ('Nadrazni',  '27', 'Krecovice', '25756', 49.7126, 14.4670),
  ('Lesni',     '2',  'Krecovice', '25756', 49.7235, 14.4690),
  ('Lesni',     '4',  'Krecovice', '25756', 49.7235, 14.4695),
  ('Lesni',     '6',  'Krecovice', '25756', 49.7236, 14.4700),
  ('Lesni',     '8',  'Krecovice', '25756', 49.7236, 14.4705),
  ('Rybnicni',  '1',  'Krecovice', '25756', 49.7105, 14.4610),
  ('Rybnicni',  '3',  'Krecovice', '25756', 49.7105, 14.4615),
  ('Rybnicni',  '5',  'Krecovice', '25756', 49.7106, 14.4620),
  ('Rybnicni',  '7',  'Krecovice', '25756', 49.7106, 14.4625);
