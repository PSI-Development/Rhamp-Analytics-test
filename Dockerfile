FROM python:3.7.9-slim
RUN mkdir /opt/rhamp_bp_analytics
WORKDIR /opt/rhamp_bp_analytics
ADD requirements.txt .
RUN pip install -r requirements.txt
ADD . .
EXPOSE 5000
ENV FLASK_APP=analytics_endpoint.py
ENV CONFIG_ANALYTICS=/opt/rhamp_bp_analytics/config_analytics.json
#CMD ["flask", "run", "--host", "0.0.0.0", "--port","80"]
CMD ["python", "./analytics_endpoint.py"]