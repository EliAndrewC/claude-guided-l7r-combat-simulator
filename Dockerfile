FROM python:3.10-slim
WORKDIR /app
COPY requirements.in .
RUN pip install --no-cache-dir streamlit pyyaml
COPY simulation/ simulation/
COPY web/ web/
COPY .streamlit/ .streamlit/
EXPOSE 8501
CMD ["streamlit", "run", "web/app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0"]
