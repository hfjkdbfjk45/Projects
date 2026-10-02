import importlib.util
import json
import math
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
NFL=ROOT/"projects/nfl-play-predictor"
sys.path.insert(0,str(NFL));sys.path.insert(0,str(ROOT));sys.path.insert(0,str(NFL/"scripts"))
from nfl.core import FourthDownSimulator,Predictor,dataset_hash,features,load_rows,make_synthetic,temporal_split
from import_nflverse import normalize
import launch

CONTEXT=dict(down=4,ydstogo=3,yardline_100=38,seconds_remaining=420,score_differential=-3,quarter=4,previous_play="pass")

class NFLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=load_rows(NFL/"data/demo_plays.csv");cls.parts=temporal_split(cls.rows)
        cls.predictor=Predictor.load(NFL/"models/baseline.json")
        cls.sim=FourthDownSimulator(cls.predictor,cls.parts[0])
    def test_probabilities_sum_to_one(self):
        p=self.predictor.predict(CONTEXT)
        self.assertGreaterEqual(p["pass_probability"],0);self.assertLessEqual(p["pass_probability"],1)
        self.assertAlmostEqual(p["pass_probability"]+p["run_probability"],1)
    def test_outcomes_are_not_features(self):
        self.assertEqual(features(CONTEXT),features({**CONTEXT,"play_type":"pass","yards_gained":99,"epa":9,"wp":1}))
    def test_invalid_features(self):
        for key,value in [("down",0),("down",True),("ydstogo",float("nan")),("seconds_remaining",float("inf")),("yardline_100",101),("quarter",5),("previous_play","future-pass")]:
            with self.subTest(key=key),self.assertRaises(ValueError):
                features({**CONTEXT,key:value})
    def test_split_disjoint_games(self):
        ids=[{r["game_id"] for r in part} for part in self.parts]
        self.assertFalse(ids[0]&ids[1]);self.assertFalse(ids[0]&ids[2]);self.assertFalse(ids[1]&ids[2])
        self.assertLess(max(r["season"] for r in self.parts[0]),min(r["season"] for r in self.parts[1]))
    def test_split_rejects_cross_season_game(self):
        rows=[dict(r) for r in self.rows];rows[-1]["game_id"]=rows[0]["game_id"]
        with self.assertRaises(ValueError):temporal_split(rows)
    def test_model_dataset_hash_matches(self):
        self.assertEqual(dataset_hash(NFL/"data/demo_plays.csv"),self.predictor.model["dataset_sha256"])
        self.assertIn("synthetic",self.predictor.model["data_source"])
    def test_generation_reproducible(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=Path(d)/"a.csv",Path(d)/"b.csv"
            make_synthetic(a,games_per_season=2,plays_per_game=4);make_synthetic(b,games_per_season=2,plays_per_game=4)
            self.assertEqual(a.read_bytes(),b.read_bytes())
    def test_simulation_reproducible(self):
        self.assertEqual(self.sim.recommend(CONTEXT,runs=100),self.sim.recommend(CONTEXT,runs=100))
    def test_strategy_intervals(self):
        result=self.sim.recommend(CONTEXT,runs=300)
        self.assertEqual({a["action"] for a in result["actions"]},{"go","field_goal","punt"})
        for a in result["actions"]:
            lo,hi=a["interval95"];self.assertTrue(0<=lo<=a["win_probability"]<=hi<=1)
    def test_recommendation_rejects_unsupported_situation(self):
        for context in [{**CONTEXT,"down":3},{**CONTEXT,"seconds_remaining":901}]:
            with self.assertRaises(ValueError):self.sim.recommend(context,runs=100)
        for runs in [0,99,5001,True]:
            with self.assertRaises(ValueError):self.sim.recommend(CONTEXT,runs=runs)
    def test_import_preceding_play_is_past_only(self):
        raw={**CONTEXT,"game_id":"2020_TEST","posteam":"DEMO","season":"2020","week":"1","qtr":"4","game_seconds_remaining":"420","play_type":"run","yards_gained":"3"}
        rows=list(normalize([{**raw,"play_id":"1"},{**raw,"play_id":"2","play_type":"pass"}]))
        self.assertEqual(rows[0]["previous_play"],"none");self.assertEqual(rows[1]["previous_play"],"run")
    def test_import_filters_kneels_and_missing_fields(self):
        raw={**CONTEXT,"game_id":"2020_TEST","posteam":"DEMO","season":"2020","week":"1","qtr":"4","game_seconds_remaining":"420","play_type":"run","yards_gained":"3","play_id":"1"}
        self.assertEqual(list(normalize([{**raw,"qb_kneel":"1"}])),[])
        self.assertEqual(list(normalize([{**raw,"ydstogo":""}])),[])

class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(("127.0.0.1",0),launch.make_handler())
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base="http://127.0.0.1:"+str(cls.server.server_port)
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()
    def call(self,path,body=None):
        request=urllib.request.Request(self.base+path,data=None if body is None else json.dumps(body).encode(),headers={"Content-Type":"application/json"})
        try:
            with urllib.request.urlopen(request,timeout=20) as r:return r.status,json.load(r)
        except urllib.error.HTTPError as e:
            return e.code,json.load(e)
    def test_health(self):self.assertEqual(self.call("/health")[0],200)
    def test_nba_api(self):
        _,sample=self.call("/api/nba/sample");status,result=self.call("/api/nba/validate",sample)
        self.assertEqual(status,200);self.assertTrue(result["validUnderImplementedRules"])
    def test_f1_api(self):
        status,result=self.call("/api/f1/simulate",dict(laps=57,runs=100,seed=42,rainProbability=.25,pitLoss=22))
        self.assertEqual(status,200);self.assertEqual(len(result["results"]),4)
    def test_nfl_api(self):
        status,result=self.call("/api/nfl/predict",CONTEXT)
        self.assertEqual(status,200);self.assertIn(result["prediction"],("pass","run"))
    def test_error_status(self):
        self.assertEqual(self.call("/api/nfl/predict",{"down":9})[0],400)
        self.assertEqual(self.call("/api/f1/simulate",dict(laps=57,runs=0,seed=42,rainProbability=0,pitLoss=22))[0],400)
        self.assertEqual(self.call("/unknown")[0],404)
    def test_source_files_not_served(self):
        self.assertEqual(self.call("/.env")[0],404)
        self.assertEqual(self.call("/launch.py")[0],404)

@unittest.skipUnless(importlib.util.find_spec("torch"),"PyTorch not installed; exercised by the ML CI job")
class TorchTests(unittest.TestCase):
    def test_future_padding_cannot_affect_prediction(self):
        import torch
        from nfl.transformer import PlayTransformer
        torch.manual_seed(42);model=PlayTransformer();model.eval()
        x=torch.randn(2,8,8);lengths=torch.tensor([3,6])
        changed=x.clone();changed[0,3:]=1000;changed[1,6:]=-1000
        with torch.inference_mode():
            self.assertTrue(torch.allclose(model(x,lengths),model(changed,lengths),atol=1e-6))
    def test_gradients_finite(self):
        import torch
        from nfl.transformer import PlayTransformer
        torch.manual_seed(42);model=PlayTransformer();x=torch.randn(2,8,8)
        loss=torch.nn.functional.binary_cross_entropy_with_logits(model(x,torch.tensor([8,5])),torch.tensor([1.,0.]))
        loss.backward();self.assertTrue(math.isfinite(loss.item()))
        self.assertTrue(all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None))

if __name__=="__main__":unittest.main()
