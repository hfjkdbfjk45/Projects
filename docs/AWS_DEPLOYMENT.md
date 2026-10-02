# Optional AWS EC2 deployment

The repository supplies deployable containers; no AWS deployment or spending has been performed. The combined offline dashboard is a local demonstration server. Deploy the containerized NFL app and NBA API if you want a remote demonstration.

1. Create an EC2 Linux instance in your own AWS account and install Git, Docker Engine, and Docker Compose using the current vendor documentation.
2. Keep inbound network access limited to SSH from your address for an initial private demonstration.
3. Clone this repository. Copy `.env.example` to `.env` and replace the demonstration database password with your own value. Do not commit credentials.
4. Run `docker compose up --build -d`. Use `docker compose ps` and `docker compose logs` to inspect health/startup.
5. Run `docker compose exec nfl python scripts/load_postgres.py` to load the demo dataset, or supply your own normalized dataset.
6. Forward the loopback-bound ports from your computer:

```bash
ssh -L 5000:127.0.0.1:5000 -L 5080:127.0.0.1:5080 ubuntu@YOUR_INSTANCE_ADDRESS
```

Open http://127.0.0.1:5000 for the React/Flask app or call http://127.0.0.1:5080/api/sample. These forwards keep the demo accessible through your SSH connection.

For a public demonstration, configure a domain, HTTPS reverse proxy, authentication/rate limits where needed, monitoring, backups, and secret management. Do not expose PostgreSQL directly. Gunicorn is used by the Docker image; Flask's development server is for local use.

The NFL model and empirical outcome pool load from local files at startup. PostgreSQL ETL is separate, and live mode needs a provider-specific normalized context endpoint. Training a Transformer or processing a large historical dataset requires separately sized compute and storage.

Primary references: [EC2 getting started](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/EC2_GetStarted.html), [Docker Engine install](https://docs.docker.com/engine/install/), [Docker Compose](https://docs.docker.com/compose/), [Flask deployment](https://flask.palletsprojects.com/en/stable/deploying/).
