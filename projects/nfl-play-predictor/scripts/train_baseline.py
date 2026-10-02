"""Train/evaluate the lightweight model. Run from any working directory."""
import argparse
import json
import sys
from pathlib import Path

PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT))
from nfl.core import dataset_hash, load_rows, make_synthetic, train_baseline

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--data",type=Path,default=PROJECT/"data/demo_plays.csv")
    parser.add_argument("--output",type=Path,default=PROJECT/"models")
    parser.add_argument("--generate-demo",action="store_true")
    parser.add_argument("--data-source",default="synthetic demo data; not observed NFL games")
    args=parser.parse_args()
    if args.generate_demo:
        make_synthetic(args.data)
    rows=load_rows(args.data)
    model,report=train_baseline(rows,args.data_source,dataset_hash(args.data))
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/"baseline.json").write_text(json.dumps(model,indent=2)+"\n")
    (args.output/"baseline_metrics.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))

if __name__=="__main__":
    main()
