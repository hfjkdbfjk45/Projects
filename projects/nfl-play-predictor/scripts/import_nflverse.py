"""Download public nflverse season CSVs and retain run/pass plays with valid pre-snap inputs."""
import argparse
import csv
import gzip
import io
import json
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path

PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT))
from nfl.core import FIELDS,dataset_hash,features,numeric

def normalize(records):
    previous=defaultdict(lambda:"none")
    last_play={}
    for raw in records:
        if raw.get("play_type") not in ("run","pass") or raw.get("qb_kneel") in ("1","1.0") or raw.get("qb_spike") in ("1","1.0"):
            continue
        game=raw.get("game_id","");team=raw.get("posteam","")
        if not game or not team:
            continue
        try:
            play_id=int(float(raw["play_id"]))
            key=game,team
            if key in last_play and play_id<=last_play[key]:
                raise RuntimeError("Source plays must be in increasing play_id order per game/offense")
            row={k:raw.get(k,"") for k in FIELDS}
            row.update(play_id=play_id,previous_play=previous[key],seconds_remaining=raw.get("game_seconds_remaining",""),quarter=raw.get("qtr",""))
            row["season"]=int(float(raw["season"]))
            row["yards_gained"]=float(raw["yards_gained"])
            numeric(row,"yards_gained",-99,99)
            numeric(row,"week",1,25,integer=True)
            if play_id<1:
                raise ValueError("Invalid play identifier")
            features(row)
        except (ValueError,TypeError,KeyError):
            continue
        previous[key]=row["play_type"];last_play[key]=play_id
        yield row

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--seasons",type=int,nargs="+",default=list(range(2014,2026)))
    p.add_argument("--output",type=Path,default=PROJECT/"data/raw/nflverse_plays.csv")
    p.add_argument("--local-gzip",type=Path,help="Normalize one previously downloaded season CSV.gz offline")
    args=p.parse_args()
    if any(y<1999 or y>2026 for y in args.seasons):
        p.error("Use available completed/current seasons from 1999 through 2026")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    paths=[];sources=[];count=0
    if args.local_gzip:
        paths=[args.local_gzip];sources=["local nflverse-format file; provenance supplied by user"]
    else:
        for season in sorted(set(args.seasons)):
            url=f"https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{season}.csv.gz"
            target=args.output.parent/f"play_by_play_{season}.csv.gz"
            if not target.exists():
                request=urllib.request.Request(url,headers={"User-Agent":"SportsAnalyticsPortfolio/1.0"})
                partial=target.with_suffix(target.suffix+".tmp")
                try:
                    with urllib.request.urlopen(request,timeout=90) as source, partial.open("wb") as dest:
                        while chunk:=source.read(1024*1024):
                            dest.write(chunk)
                    partial.replace(target)
                finally:
                    partial.unlink(missing_ok=True)
            paths.append(target);sources.append(url)
    # Write atomically: failed downloads/normalization never replace an earlier combined dataset.
    temporary=args.output.with_suffix(args.output.suffix+".tmp")
    try:
        with temporary.open("w",newline="") as dest:
            writer=csv.DictWriter(dest,FIELDS);writer.writeheader()
            for path in paths:
                with gzip.open(path,"rt",newline="") as source:
                    for row in normalize(csv.DictReader(source)):
                        writer.writerow(row);count+=1
        if count==0:
            raise ValueError("No eligible plays were imported")
        temporary.replace(args.output)
    finally:
        temporary.unlink(missing_ok=True)
    metadata=dict(source="nflverse public historical play-by-play",sources=sources,rows=count,
                  sha256=dataset_hash(args.output),filters="run/pass; exclude spikes/kneels; complete finite pre-snap inputs; regulation quarters")
    args.output.with_suffix(".metadata.json").write_text(json.dumps(metadata,indent=2)+"\n")
    print(json.dumps(metadata,indent=2))

if __name__=="__main__":
    main()
