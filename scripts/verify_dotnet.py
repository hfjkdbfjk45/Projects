"""CI: normalize fixture data and validate the real Java -> .NET API chain."""
import csv
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def main():
    subprocess.run(["dotnet","run","--project","projects/f1-strategy-simulator/pipeline","--no-build","--","--fixture","projects/f1-strategy-simulator/data/openf1-fixture.json","--output","output/f1-telemetry"],cwd=ROOT,check=True)
    rows=list(csv.DictReader((ROOT/"output/f1-telemetry/laps_normalized.csv").open()))
    assert len(rows)==4
    first=next(r for r in rows if r["driver_number"]=="1" and r["lap_number"]=="1")
    stop=next(r for r in rows if r["driver_number"]=="1" and r["lap_number"]=="3")
    assert first["tyre_age"]=="0" and stop["compound"]=="HARD" and stop["tyre_age"]=="1"
    assert float(stop["pit_lane_seconds"])==22.2 and float(stop["stationary_stop_seconds"])==2.4
    engine=subprocess.Popen(["java","-cp","build","TradeServer","serve",".","8081"],cwd=ROOT)
    api=subprocess.Popen(["dotnet","run","--project","projects/nba-trade-machine/api","--no-build","--urls","http://127.0.0.1:5080"],cwd=ROOT)
    try:
        for _ in range(60):
            try:
                with urllib.request.urlopen("http://127.0.0.1:5080/health",timeout=1) as r:
                    assert json.load(r)["engine"]=="java"
                break
            except OSError:
                time.sleep(.5)
        else:
            raise AssertionError("Middleware never became healthy")
        sample=(ROOT/"projects/nba-trade-machine/data/sample-trade.json").read_bytes()
        request=urllib.request.Request("http://127.0.0.1:5080/api/validate",data=sample,headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(request) as r:
            assert json.load(r)["validUnderImplementedRules"] is True
        print(".NET pipeline and Java/API chain passed")
    finally:
        api.terminate();engine.terminate();api.wait(timeout=10);engine.wait(timeout=10)

if __name__=="__main__":main()
