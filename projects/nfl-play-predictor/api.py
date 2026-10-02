"""Flask API for the React dashboard; baseline is default, transformer is opt-in."""
import json
import os
import urllib.request
from pathlib import Path
from flask import Flask,jsonify,request,send_from_directory
from nfl.core import FourthDownSimulator,Predictor,features,load_rows,temporal_split

PROJECT=Path(__file__).resolve().parent

def create_app():
    app=Flask(__name__,static_folder=None)
    app.config["MAX_CONTENT_LENGTH"]=65536
    baseline=Predictor.load(os.environ.get("NFL_BASELINE_MODEL",str(PROJECT/"models/baseline.json")))
    data=Path(os.environ.get("NFL_TRAINING_DATA",str(PROJECT/"data/demo_plays.csv")))
    simulator=FourthDownSimulator(baseline,temporal_split(load_rows(data))[0])
    transformer=None
    if checkpoint:=os.environ.get("NFL_TRANSFORMER_MODEL"):
        from nfl.transformer import TransformerPredictor
        metadata=json.loads(Path(checkpoint).with_name("metadata.json").read_text())
        transformer=TransformerPredictor(checkpoint,metadata)
    def predict(value):
        if not isinstance(value,dict):
            raise ValueError("Expected an object")
        if transformer:
            return transformer.predict(value.get("contexts",[value]))
        return baseline.predict(value)
    @app.errorhandler(ValueError)
    def bad_input(error):
        return jsonify(error=str(error)),400
    @app.get("/health")
    def health():
        return jsonify(status="ok",model="transformer" if transformer else "logistic baseline",data_source=transformer.metadata["data_source"] if transformer else baseline.model["data_source"])
    @app.post("/api/predict")
    def predict_route():
        return jsonify(predict(request.get_json()))
    @app.post("/api/recommend")
    def recommend_route():
        value=request.get_json()
        if not isinstance(value,dict):
            raise ValueError("Expected an object")
        return jsonify(simulator.recommend(value,runs=value.get("runs",2000),seed=value.get("seed",42)))
    @app.get("/api/metrics")
    def metric_route():
        return jsonify(baseline.model["evaluation"])
    @app.get("/api/live")
    def live_route():
        # A provider must expose the normalized pre-snap context schema; this does not invent a live NFL feed.
        url=os.environ.get("NFL_LIVE_URL")
        if not url:
            return jsonify(error="Configure NFL_LIVE_URL for your licensed provider's normalized context endpoint"),503
        headers={"Accept":"application/json"}
        if token:=os.environ.get("NFL_LIVE_TOKEN"):
            headers["Authorization"]="Bearer "+token
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=8) as response:
                body=response.read(65537)
            if len(body)>65536:
                raise ValueError("Provider response too large")
            value=json.loads(body)
            result=predict(value)
            return jsonify(context=value,prediction=result,source="configured external provider")
        except (OSError,ValueError):
            return jsonify(error="Unable to obtain a valid live pre-snap context"),502
    @app.get("/")
    def index():
        if not (PROJECT/"frontend/dist/index.html").exists():
            return jsonify(message="Build the React frontend first: cd frontend && npm install && npm run build")
        return send_from_directory(PROJECT/"frontend/dist","index.html")
    @app.get("/assets/<path:name>")
    def assets(name):
        return send_from_directory(PROJECT/"frontend/dist/assets",name)
    return app

app=create_app()
if __name__=="__main__":
    app.run(host="127.0.0.1",port=5000)
