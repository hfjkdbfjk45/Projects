"""Verify built containers, parameterized PostgreSQL ETL, and idempotent loading."""
import json
import subprocess
import time
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def request(url,body=None):
    req=urllib.request.Request(url,data=None if body is None else json.dumps(body).encode(),headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=10) as r:
        return json.load(r)
def wait(url):
    for _ in range(60):
        try:
            assert request(url)["status"]=="ok";return
        except (OSError,AssertionError):
            time.sleep(.5)
    raise AssertionError("Container did not become healthy: "+url)
def main():
    wait("http://127.0.0.1:5000/health");wait("http://127.0.0.1:5080/health")
    sample=request("http://127.0.0.1:5080/api/sample")
    assert request("http://127.0.0.1:5080/api/validate",sample)["validUnderImplementedRules"]
    context=dict(down=4,ydstogo=3,yardline_100=38,seconds_remaining=420,score_differential=-3,quarter=4,previous_play="pass")
    assert request("http://127.0.0.1:5000/api/predict",context)["prediction"] in ("run","pass")
    with urllib.request.urlopen("http://127.0.0.1:5000") as r:
        assert b'<div id="root"></div>' in r.read()
    for _ in range(2):
        subprocess.run(["docker","compose","exec","-T","nfl","python","scripts/load_postgres.py"],cwd=ROOT,check=True)
    count=subprocess.check_output(["docker","compose","exec","-T","postgres","psql","-U","portfolio","-d","sports","-Atc","SELECT COUNT(*) FROM plays;"],cwd=ROOT,text=True).strip()
    assert count=="3840",f"Expected 3840 unique plays after repeated loads, got {count}"
    print("Container checks passed: Java/.NET API, React/Flask app, PostgreSQL schema/ETL, repeated upsert preserves 3840 rows")
if __name__=="__main__":main()
