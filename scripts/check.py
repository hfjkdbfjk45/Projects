#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import launch

def main():
    launch.compile_java()
    import shutil
    java=shutil.which("java");javac=shutil.which("javac")
    compiler=[javac] if javac else [java,"com.sun.tools.javac.Main"]
    subprocess.run([*compiler,"-cp",str(ROOT/"build"),"-d",str(ROOT/"build"),str(ROOT/"tests/PortfolioJavaTests.java")],check=True)
    subprocess.run([java,"-cp",str(ROOT/"build"),"PortfolioJavaTests",str(ROOT)],check=True,cwd=ROOT)
    subprocess.run([sys.executable,"-m","unittest","discover","-s","tests","-p","test_*.py","-v"],check=True,cwd=ROOT)
    if shutil.which("node"):
        subprocess.run(["node","--check","dashboard/app.js"],check=True,cwd=ROOT)

if __name__=="__main__":main()
