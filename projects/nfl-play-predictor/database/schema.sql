CREATE TABLE IF NOT EXISTS plays (
  game_id TEXT NOT NULL,
  play_id INTEGER NOT NULL,
  season SMALLINT NOT NULL CHECK (season >= 1999),
  week SMALLINT NOT NULL,
  posteam TEXT NOT NULL,
  down SMALLINT NOT NULL CHECK (down BETWEEN 1 AND 4),
  ydstogo DOUBLE PRECISION NOT NULL CHECK (ydstogo BETWEEN 1 AND 99),
  yardline_100 DOUBLE PRECISION NOT NULL CHECK (yardline_100 BETWEEN 1 AND 99),
  seconds_remaining DOUBLE PRECISION NOT NULL CHECK (seconds_remaining BETWEEN 1 AND 3600),
  score_differential DOUBLE PRECISION NOT NULL,
  quarter SMALLINT NOT NULL CHECK (quarter BETWEEN 1 AND 4),
  previous_play TEXT NOT NULL CHECK (previous_play IN ('none','run','pass')),
  play_type TEXT NOT NULL CHECK (play_type IN ('run','pass')),
  yards_gained DOUBLE PRECISION NOT NULL,
  PRIMARY KEY (game_id,play_id)
);
CREATE INDEX IF NOT EXISTS plays_season_idx ON plays (season);
CREATE INDEX IF NOT EXISTS plays_situation_idx ON plays (down,ydstogo,play_type);
