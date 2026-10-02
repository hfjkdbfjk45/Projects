"""Portable logistic baseline and empirical Monte Carlo game continuation.

Only pre-snap information is used as prediction input. Bundled training data is
synthetic; historical NFL training is a separate, explicit workflow.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path

FEATURES = ["intercept", "down", "log_distance", "field_position", "time_remaining", "score_difference", "quarter", "previous_call", "down_distance"]
FIELDS = ["game_id", "season", "week", "play_id", "posteam", "down", "ydstogo", "yardline_100", "seconds_remaining", "score_differential", "quarter", "previous_play", "play_type", "yards_gained"]


def numeric(context, key, lo, hi, *, integer=False):
    value = context.get(key)
    if isinstance(value, bool):
        raise ValueError(f"Invalid {key}")
    try:
        x = float(value)
    except (ValueError, TypeError):
        raise ValueError(f"Missing or invalid {key}") from None
    if not math.isfinite(x) or not lo <= x <= hi or (integer and x != int(x)):
        raise ValueError(f"{key} must be {'an integer' if integer else 'a number'} between {lo} and {hi}")
    return int(x) if integer else x


def features(context):
    down = numeric(context, "down", 1, 4, integer=True)
    distance = numeric(context, "ydstogo", 1, 99)
    field = numeric(context, "yardline_100", 1, 99)
    seconds = numeric(context, "seconds_remaining", 1, 3600)
    score = numeric(context, "score_differential", -80, 80)
    quarter = numeric(context, "quarter", 1, 4, integer=True)
    previous = context.get("previous_play", "none")
    if previous not in ("none", "run", "pass"):
        raise ValueError("previous_play must be none, run, or pass")
    d = (down - 2.5) / 1.5
    length = math.log1p(distance) / math.log(21)
    return [1.0, d, length, (field - 50) / 50, (seconds - 1800) / 1800,
            score / 21, (quarter - 2.5) / 1.5, {"none": 0, "run": -1, "pass": 1}[previous], d * length]


def sigmoid(x):
    if x >= 0:
        return 1 / (1 + math.exp(-min(x, 700)))
    e = math.exp(max(x, -700))
    return e / (1 + e)


def make_synthetic(path, seed=42, games_per_season=12, plays_per_game=40):
    rng = random.Random(seed)
    rows = []
    for season in range(2018, 2026):
        for game in range(games_per_season):
            previous = "none"
            for play in range(plays_per_game):
                down = rng.choices([1, 2, 3, 4], [0.42, 0.32, 0.23, 0.03])[0]
                distance = rng.choice([1, 2, 3, 4, 5, 6, 7, 10, 10, 10, 12, 15])
                row = dict(game_id=f"{season}_DEMO_{game:03d}", season=season, week=game + 1, play_id=play + 1,
                           posteam="DEMO", down=down, ydstogo=distance, yardline_100=rng.randint(5, 95),
                           seconds_remaining=max(1, 3600-play*85), score_differential=rng.choice([-14,-7,-3,0,3,7,14]),
                           quarter=min(4, play//10+1), previous_play=previous)
                x = features(row)
                # This is a generative demo distribution, not a fitted NFL probability.
                logit = -1.8 + 0.7*x[1] + 2.8*x[2] - 0.25*x[3] - 0.3*x[4] - 0.7*x[5] + 0.2*x[6] + 0.22*x[7]
                call = "pass" if rng.random() < sigmoid(logit) else "run"
                if call == "pass":
                    gained = 0 if rng.random() < .32 else int(round(rng.gauss(8.5, 9)))
                else:
                    gained = int(round(rng.gauss(4.4, 4.6)))
                row.update(play_type=call, yards_gained=max(-12, min(65, gained)))
                rows.append(row)
                previous = call
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return rows


def load_rows(path):
    with Path(path).open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise ValueError("Dataset is empty")
    seen = set()
    for row in rows:
        features(row)
        if row["play_type"] not in ("run", "pass"):
            raise ValueError("Dataset must contain only eligible run/pass plays")
        row["season"] = int(row["season"])
        row["play_id"] = int(row["play_id"])
        row["yards_gained"] = numeric(row, "yards_gained", -99, 99)
        key = row["game_id"], row["play_id"]
        if key in seen:
            raise ValueError("Duplicate game_id/play_id")
        seen.add(key)
    return rows


def temporal_split(rows):
    seasons = sorted({int(r["season"]) for r in rows})
    if len(seasons) < 3:
        raise ValueError("Provide at least three seasons for train/validation/test separation")
    split = [[r for r in rows if int(r["season"]) in seasons[:-2]],
             [r for r in rows if int(r["season"]) == seasons[-2]],
             [r for r in rows if int(r["season"]) == seasons[-1]]]
    game_sets = [{r["game_id"] for r in part} for part in split]
    if any(game_sets[i] & game_sets[j] for i in range(3) for j in range(i + 1, 3)):
        raise ValueError("A game appears in multiple season splits")
    return split


def metrics(rows, probabilities):
    labels = [int(r["play_type"] == "pass") for r in rows]
    predictions = [int(p >= .5) for p in probabilities]
    tp = sum(y == p == 1 for y, p in zip(labels, predictions))
    tn = sum(y == p == 0 for y, p in zip(labels, predictions))
    fp = sum(y == 0 and p == 1 for y, p in zip(labels, predictions))
    fn = sum(y == 1 and p == 0 for y, p in zip(labels, predictions))
    return dict(rows=len(labels), accuracy=(tp+tn)/len(labels), f1=2*tp/max(1,2*tp+fp+fn),
                balanced_accuracy=.5*(tp/max(1,tp+fn)+tn/max(1,tn+fp)),
                brier=sum((p-y)**2 for p,y in zip(probabilities, labels))/len(labels),
                confusion_matrix={"true_pass":tp,"true_run":tn,"false_pass":fp,"false_run":fn})


def train_baseline(rows, data_source, dataset_sha256, epochs=180):
    train, validation, test = temporal_split(rows)
    x = [features(r) for r in train]
    y = [int(r["play_type"] == "pass") for r in train]
    weights = [0.0] * len(FEATURES)
    best, best_score = weights[:], float("inf")
    for epoch in range(epochs):
        grad = [0.0] * len(weights)
        for row, label in zip(x, y):
            residual = sigmoid(sum(w*a for w,a in zip(weights,row))) - label
            for j, a in enumerate(row):
                grad[j] += residual*a
        for j in range(len(weights)):
            weights[j] -= .65*(grad[j]/len(x) + (0 if j == 0 else .003*weights[j]))
        if epoch % 5 == 0 or epoch == epochs-1:
            probs = [sigmoid(sum(w*a for w,a in zip(weights,features(r)))) for r in validation]
            score = metrics(validation, probs)["brier"]
            if score < best_score:
                best_score, best = score, weights[:]
    majority = int(sum(y) >= len(y)/2)
    report = dict(model="logistic baseline", data_source=data_source, dataset_sha256=dataset_sha256, seed=42,
                  features=FEATURES, splits={k:dict(rows=len(v),games=len({r["game_id"] for r in v}),seasons=sorted({int(r["season"]) for r in v}))
                  for k,v in zip(["train","validation","test"],[train,validation,test])})
    report["test"] = metrics(test, [sigmoid(sum(w*a for w,a in zip(best, features(r)))) for r in test])
    report["majority_baseline_accuracy"] = sum(int(r["play_type"] == "pass") == majority for r in test)/len(test)
    model = dict(version=1, model_type="logistic", weights=best, features=FEATURES, data_source=data_source,
                 dataset_sha256=dataset_sha256, evaluation=report)
    return model, report


class Predictor:
    def __init__(self, model):
        if model.get("version") != 1 or model.get("features") != FEATURES or len(model.get("weights", [])) != len(FEATURES):
            raise ValueError("Incompatible model")
        if any(not math.isfinite(float(w)) for w in model["weights"]):
            raise ValueError("Invalid model weights")
        self.model = model

    @classmethod
    def load(cls, path):
        return cls(json.loads(Path(path).read_text()))

    def probability(self, context):
        return sigmoid(sum(w*x for w,x in zip(self.model["weights"], features(context))))

    def predict(self, context):
        p = self.probability(context)
        return dict(prediction="pass" if p >= .5 else "run", pass_probability=p, run_probability=1-p,
                    model=self.model["model_type"], data_source=self.model["data_source"],
                    note="A run/pass classifier; probabilities are not calibrated win probabilities.")


class FourthDownSimulator:
    """Bootstrap play outcomes, simulate possession changes and a simplified remaining game.

    Illustrative strategy comparison, not a calibrated professional NFL win model.
    Only training-split outcomes are placed in the bootstrap pool.
    """
    def __init__(self, predictor, training_rows):
        self.predictor = predictor
        self.pools = defaultdict(list)
        for row in training_rows:
            self.pools[row["play_type"], self.bucket(float(row["ydstogo"]))].append(float(row["yards_gained"]))
        if not self.pools:
            raise ValueError("Training outcome pool is empty")

    @staticmethod
    def bucket(distance):
        return "short" if distance <= 3 else "medium" if distance <= 7 else "long"

    def gain(self, rng, call, distance):
        pool = self.pools.get((call, self.bucket(distance)))
        if not pool:
            pool = [v for (c,_), values in self.pools.items() if c == call for v in values]
        if not pool:
            raise ValueError(f"No {call} outcomes available")
        return rng.choice(pool)

    @staticmethod
    def field_goal_probability(field):
        return sigmoid((53-(field+17))/9)

    def recommend(self, context, runs=2000, seed=42):
        features(context)
        if numeric(context, "down", 1, 4, integer=True) != 4:
            raise ValueError("Recommendations require fourth down")
        if not isinstance(runs, int) or isinstance(runs,bool) or not 100 <= runs <= 5000:
            raise ValueError("runs must be an integer from 100 to 5000")
        if not isinstance(seed,int) or isinstance(seed,bool) or not 0<=seed<=2147483647:
            raise ValueError("seed must be an integer from 0 to 2147483647")
        field = numeric(context,"yardline_100",1,99)
        distance = numeric(context,"ydstogo",1,99)
        seconds = numeric(context,"seconds_remaining",1,900)
        score = numeric(context,"score_differential",-80,80)
        p_pass = self.predictor.probability(context)
        actions = []
        for action in ("go", "field_goal", "punt"):
            outcomes=[]
            for i in range(runs):
                rng=random.Random(seed+i*7919)
                side, position, differential, clock = 1, field, score, seconds
                if action=="go":
                    call="pass" if rng.random()<p_pass else "run"
                    yards=self.gain(rng,call,distance)
                    clock-=10 if call=="pass" and yards==0 else 30
                    if yards>=position:
                        differential+=7;side=-1;position=75
                    elif yards>=distance:
                        position=max(1,position-yards)
                    else:
                        side=-1;position=min(99,max(1,100-(position-yards)))
                elif action=="field_goal":
                    success=rng.random()<self.field_goal_probability(position)
                    differential+=3 if success else 0
                    side=-1;position=75 if success else min(99,max(1,100-position-7));clock-=7
                else:
                    side=-1;position=min(80,max(1,100-position+max(15,rng.gauss(40,8))));clock-=10
                while clock>0:
                    points, duration, next_position=self.drive(rng,position,clock)
                    differential+=side*points;clock-=duration;side*=-1;position=next_position
                outcomes.append(1 if differential>0 else .5 if differential==0 else 0)
            probability=sum(outcomes)/runs
            variance=sum((x-probability)**2 for x in outcomes)/max(1,runs-1)
            se=math.sqrt(variance/runs)
            actions.append(dict(action=action,win_probability=probability,monte_carlo_standard_error=se,
                                interval95=[max(0,probability-1.96*se),min(1,probability+1.96*se)]))
        actions.sort(key=lambda a:a["win_probability"],reverse=True)
        return dict(recommendation=actions[0]["action"],actions=actions,runs=runs,seed=seed,data_source=self.predictor.model["data_source"],
                    model="empirical bootstrap with simplified clock, drive and kicking assumptions",
                    note="Uncalibrated estimates; ties count as half a win. Intervals cover Monte Carlo sampling error only, not model error.")

    def drive(self,rng,field,clock):
        down,distance,spent=1,min(10,field),0
        for _ in range(18):
            if down==4:
                if field<=35:
                    return (3 if rng.random()<self.field_goal_probability(field) else 0),spent+7,75
                return 0,spent+10,min(80,max(1,100-field+max(15,rng.gauss(40,8))))
            call="pass" if rng.random()<(.72 if down==3 and distance>3 else .55) else "run"
            gain=self.gain(rng,call,distance)
            spent+=10 if call=="pass" and gain==0 else 30
            if spent>clock:
                return 0,spent,75
            if gain>=field:
                return 7,spent,75
            field=min(99,max(1,field-gain))
            if gain>=distance:
                down,distance=1,min(10,field)
            else:
                down+=1;distance=min(99,max(1,distance-gain))
        return 0,max(1,spent),min(99,max(1,100-field))


def dataset_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
