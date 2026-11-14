FROM gcr.io/toms-gym/bowling-service:perf-base-93378b0
COPY profile_analyze.py numposes.py prof_app.py /app/prof/
CMD ["gunicorn", "-b", "0.0.0.0:8080", "--timeout", "870", "--workers", "1", "--threads", "1", "--chdir", "/app/prof", "prof_app:app"]
