CREATE TABLE reviews (
  id            BIGSERIAL PRIMARY KEY,
  restaurant_id TEXT NOT NULL,
  author_id     TEXT NOT NULL,
  rating        SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
  text          TEXT,
  UNIQUE (restaurant_id, author_id)
);
