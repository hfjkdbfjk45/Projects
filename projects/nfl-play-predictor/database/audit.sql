-- Data volume and target balance by season, not a claim of 2M records.
SELECT season, COUNT(*) AS plays, COUNT(DISTINCT game_id) AS games,
       AVG(CASE WHEN play_type='pass' THEN 1.0 ELSE 0.0 END) AS pass_rate
FROM plays GROUP BY season ORDER BY season;
-- The primary key prevents duplicates. This query should return zero rows.
SELECT game_id, play_id, COUNT(*) FROM plays GROUP BY game_id, play_id HAVING COUNT(*) > 1;
