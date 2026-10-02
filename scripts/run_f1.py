#!/usr/bin/env python3
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import launch
def main():
    p=argparse.ArgumentParser();p.add_argument("--runs",type=int,default=1000);p.add_argument("--laps",type=int,default=57)
    p.add_argument("--rain",type=float,default=.25);p.add_argument("--pit-loss",type=float,default=22);p.add_argument("--seed",type=int,default=42)
    p.add_argument("--output",type=Path,default=ROOT/"output/f1")
    args=p.parse_args();launch.compile_java()
    request=dict(laps=args.laps,runs=args.runs,seed=args.seed,rainProbability=args.rain,pitLoss=args.pit_loss)
    result=subprocess.run([shutil.which("java"),"-cp",str(ROOT/"build"),"RaceSimulator","--export",str(args.output)],input=json.dumps(request),text=True,capture_output=True,cwd=ROOT)
    if result.returncode:p.error(result.stderr.strip())
    value=json.loads(result.stdout)
    print(json.dumps({k:v for k,v in value.items() if k!="lapTrace"},indent=2))
    print("CSV/JSON exports:",args.output)
if __name__=="__main__":main()
