FROM python:3.12-slim
 
WORKDIR /app
 
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
 
COPY xrp_alert.py .
 
CMD ["python", "-u", "xrp_alert.py"]