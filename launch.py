#!/usr/bin/env python3
"""Run all three portfolio demos with Python 3.10+ and a Java 17+ compiler module."""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
import sys
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parent
NFL=ROOT/"projects/nfl-play-predictor"
sys.path.insert(0,str(NFL))
from nfl.core import FourthDownSimulator,Predictor,load_rows,temporal_split

def compile_java():
    java=shutil.which("java")
    if not java:
        raise RuntimeError("Install Java 17+ (JDK); java was not found")
    sources=[ROOT/"shared/java/Json.java",*(ROOT/"projects/nba-trade-machine/java").glob("*.java"),*(ROOT/"projects/f1-strategy-simulator/java").glob("*.java")]
    (ROOT/"build").mkdir(exist_ok=True)
    javac=shutil.which("javac")
    compiler=[javac] if javac else [java,"com.sun.tools.javac.Main"]
    result=subprocess.run([*compiler,"-d",str(ROOT/"build"),*map(str,sources)],capture_output=True,text=True,timeout=60)
    if result.returncode:
        raise RuntimeError("Java compilation failed: "+result.stderr[:3000])

def java_call(name,request):
    command=[shutil.which("java"),"-cp",str(ROOT/"build"),name]
    if name=="TradeServer":
        command.extend(["validate",str(ROOT)])
    result=subprocess.run(command,input=json.dumps(request,allow_nan=False),capture_output=True,text=True,cwd=ROOT,timeout=20)
    if result.returncode:
        raise ValueError(result.stderr.strip()[:500] or "Java request failed")
    return json.loads(result.stdout)

def make_handler():
    predictor=Predictor.load(NFL/"models/baseline.json")
    simulator=FourthDownSimulator(predictor,temporal_split(load_rows(NFL/"data/demo_plays.csv"))[0])
    assets={"/":("dashboard/index.html","text/html; charset=utf-8"),
            "/styles.css":("dashboard/styles.css","text/css; charset=utf-8"),
            "/app.js":("dashboard/app.js","text/javascript; charset=utf-8")}
    class Handler(BaseHTTPRequestHandler):
        def send_json(self,status,value):
            self.send_bytes(status,json.dumps(value,allow_nan=False).encode(),"application/json")
        def send_bytes(self,status,body,mime):
            self.send_response(status)
            self.send_header("Content-Type",mime)
            self.send_header("Content-Length",str(len(body)))
            self.send_header("X-Content-Type-Options","nosniff")
            self.end_headers();self.wfile.write(body)
        def do_GET(self):
            path=urlsplit(self.path).path
            if path in assets:
                file,mime=assets[path];self.send_bytes(200,(ROOT/file).read_bytes(),mime)
            elif path=="/health":
                self.send_json(200,dict(status="ok",mode="offline demo",engines=["Java NBA","Java F1","Python NFL baseline"]))
            elif path=="/api/nba/sample":
                self.send_json(200,json.loads((ROOT/"projects/nba-trade-machine/data/sample-trade.json").read_text()))
            elif path=="/api/nfl/metrics":
                self.send_json(200,predictor.model["evaluation"])
            else:
                self.send_json(404,dict(error="Not found"))
        def do_POST(self):
            try:
                size=int(self.headers.get("Content-Length","0"))
                if not 0<size<=65536:
                    self.send_json(413,dict(error="Use a JSON body of at most 64 KB"));return
                value=json.loads(self.rfile.read(size))
                if not isinstance(value,dict):
                    raise ValueError("Expected a JSON object")
                path=urlsplit(self.path).path
                if path=="/api/nba/validate":
                    result=java_call("TradeServer",value)
                elif path=="/api/f1/simulate":
                    result=java_call("RaceSimulator",value)
                elif path=="/api/nfl/predict":
                    result=predictor.predict(value)
                elif path=="/api/nfl/recommend":
                    result=simulator.recommend(value,runs=value.get("runs",2000),seed=value.get("seed",42))
                else:
                    self.send_json(404,dict(error="Not found"));return
                self.send_json(200,result)
            except (ValueError,KeyError,TypeError) as e:
                self.send_json(400,dict(error=str(e)))
            except subprocess.TimeoutExpired:
                self.send_json(504,dict(error="Simulation timed out"))
        def log_message(self,fmt,*args):
            print(fmt%args,file=sys.stderr)
    return Handler

def main():
    p=argparse.ArgumentParser();p.add_argument("--port",type=int,default=8000);p.add_argument("--check",action="store_true")
    args=p.parse_args();compile_java()
    if args.check:
        print("Java engines compiled successfully");return
    server=ThreadingHTTPServer(("127.0.0.1",args.port),make_handler())
    print(f"ScoreLab: http://127.0.0.1:{args.port} (Ctrl+C to stop)",flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__=="__main__":
    main()
