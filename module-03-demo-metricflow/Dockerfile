# Runs the demo without installing anything on the host except Docker.
# Build:  docker build -t esi-metricflow-demo .
# Run:    docker run -it --rm esi-metricflow-demo
# Then, inside the container:  mf query --metrics net_revenue --group-by metric_time__fiscal_quarter
FROM python:3.13-slim
WORKDIR /demo
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV DBT_PROFILES_DIR=/demo
RUN dbt build
CMD ["bash"]
