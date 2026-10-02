FROM node:22-alpine AS frontend
WORKDIR /repo/projects/nfl-play-predictor/frontend
COPY projects/nfl-play-predictor/frontend/ ./
COPY dashboard/styles.css /repo/dashboard/styles.css
RUN npm install && npm run build

FROM python:3.12-slim
WORKDIR /app
COPY projects/nfl-play-predictor/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY projects/nfl-play-predictor/ ./
COPY --from=frontend /repo/projects/nfl-play-predictor/frontend/dist ./frontend/dist
RUN useradd --create-home appuser
USER appuser
EXPOSE 5000
CMD ["gunicorn","--bind","0.0.0.0:5000","--workers","2","--timeout","60","api:app"]
