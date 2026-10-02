"""Train on earlier seasons, select on the penultimate season, evaluate once on the final season."""
import argparse
import copy
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT))
import torch
from torch.utils.data import DataLoader,Dataset
from nfl.core import dataset_hash,features,load_rows,metrics,temporal_split
from nfl.transformer import PlayTransformer

class SequenceDataset(Dataset):
    def __init__(self,rows,max_length=8):
        self.sequences=[];self.labels=[];self.rows=[]
        grouped=defaultdict(list)
        for row in rows:
            grouped[row["game_id"],row["posteam"]].append(row)
        for key in sorted(grouped):
            history=[]
            for row in sorted(grouped[key],key=lambda r:r["play_id"]):
                history.append(features(row)[1:])
                self.sequences.append(torch.tensor(history[-max_length:],dtype=torch.float32))
                self.labels.append(float(row["play_type"]=="pass"));self.rows.append(row)
    def __len__(self):
        return len(self.labels)
    def __getitem__(self,i):
        return self.sequences[i],self.labels[i]

def collate(batch):
    seq,labels=zip(*batch)
    return torch.nn.utils.rnn.pad_sequence(seq,batch_first=True),torch.tensor([len(s) for s in seq]),torch.tensor(labels)

def evaluate(model,dataset):
    probs=[]
    model.eval()
    with torch.inference_mode():
        for x,lengths,_ in DataLoader(dataset,batch_size=256,collate_fn=collate):
            probs.extend(torch.sigmoid(model(x,lengths)).tolist())
    return metrics(dataset.rows,probs)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--data",type=Path,default=PROJECT/"data/demo_plays.csv")
    p.add_argument("--output",type=Path,default=PROJECT/"output/transformer")
    p.add_argument("--epochs",type=int,default=15)
    p.add_argument("--data-source",default="synthetic demo data; not observed NFL games")
    args=p.parse_args()
    if not 1<=args.epochs<=200:
        p.error("--epochs must be between 1 and 200")
    random.seed(42);torch.manual_seed(42);torch.set_num_threads(2)
    rows=load_rows(args.data)
    splits=temporal_split(rows)
    train,val,test=[SequenceDataset(part) for part in splits]
    architecture=dict(n_features=8,width=32,heads=4,layers=2,max_length=8)
    model=PlayTransformer(**architecture)
    optimizer=torch.optim.AdamW(model.parameters(),lr=.001,weight_decay=.01)
    criterion=torch.nn.BCEWithLogitsLoss()
    loader=DataLoader(train,batch_size=128,shuffle=True,collate_fn=collate,generator=torch.Generator().manual_seed(42))
    best=None;best_score=float("inf");history=[]
    for epoch in range(args.epochs):
        model.train();loss_sum=0
        for x,lengths,y in loader:
            optimizer.zero_grad();loss=criterion(model(x,lengths),y)
            loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1.0);optimizer.step()
            loss_sum+=loss.item()*len(y)
        report=evaluate(model,val)
        history.append(dict(epoch=epoch+1,train_loss=loss_sum/len(train),validation_brier=report["brier"]))
        if report["brier"]<best_score:
            best_score=report["brier"];best=copy.deepcopy(model.state_dict())
        print(json.dumps(history[-1]))
    model.load_state_dict(best)
    report=dict(model="causal transformer",data_source=args.data_source,dataset_sha256=dataset_hash(args.data),
                seed=42,architecture=architecture,history=history,test=evaluate(model,test),
                splits={name:dict(rows=len(part),games=len({r["game_id"] for r in part}),seasons=sorted({r["season"] for r in part}))
                        for name,part in zip(["train","validation","test"],splits)})
    args.output.mkdir(parents=True,exist_ok=True)
    torch.save(model.state_dict(),args.output/"model.pt")
    (args.output/"metadata.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report["test"],indent=2))

if __name__=="__main__":
    main()
