CREATE TABLE addresses (
  id              BIGSERIAL PRIMARY KEY,
  owner_type      TEXT NOT NULL,
  owner_id        TEXT NOT NULL,
  street          TEXT NOT NULL,
  building_number TEXT NOT NULL,
  city            TEXT NOT NULL,
  postal_code     TEXT NOT NULL,
  lat             DOUBLE PRECISION NOT NULL,
  lon             DOUBLE PRECISION NOT NULL
);

CREATE INDEX idx_addresses_owner ON addresses (owner_type, owner_id);
