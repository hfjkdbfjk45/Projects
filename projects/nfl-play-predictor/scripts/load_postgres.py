"""Idempotent parameterized ETL. Credentials come from DATABASE_URL, never source code."""
import argparse
import csv
import os
import sys
from pathlib import Path

PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT))
from nfl.core import FIELDS,features

def main():
    import psycopg
    p=argparse.ArgumentParser();p.add_argument("--data",type=Path,default=PROJECT/"data/demo_plays.csv")
    args=p.parse_args()
    url=os.environ.get("DATABASE_URL")
    if not url:
        p.error("Set DATABASE_URL in your environment")
    columns=",".join(FIELDS)
    placeholders=",".join(["%s"]*len(FIELDS))
    updates=",".join(f"{k}=EXCLUDED.{k}" for k in FIELDS if k not in ("game_id","play_id"))
    statement=f"INSERT INTO plays ({columns}) VALUES ({placeholders}) ON CONFLICT (game_id,play_id) DO UPDATE SET {updates}"
    count=0
    with psycopg.connect(url) as connection:
        with connection.cursor() as cursor:
            cursor.execute((PROJECT/"database/schema.sql").read_text())
            batch=[]
            with args.data.open(newline="") as stream:
                for row in csv.DictReader(stream):
                    features(row)
                    batch.append([row[k] for k in FIELDS]);count+=1
                    if len(batch)==1000:
                        cursor.executemany(statement,batch);batch=[]
                if batch:
                    cursor.executemany(statement,batch)
    print(f"Loaded {count} rows; existing game/play keys were updated")

if __name__=="__main__":
    main()
