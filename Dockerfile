FROM python:3.10-slim
WORKDIR /app
COPY requirements.in .
RUN pip install --no-cache-dir streamlit==1.54.0 pyyaml
COPY simulation/ simulation/
COPY web/ web/
COPY .streamlit/ .streamlit/
EXPOSE 8501
# Use web/launcher.py instead of `streamlit run` directly so the
# launcher's patch to ``make_url_path_regex`` lands BEFORE Streamlit's
# Server class registers its ``_stcore/*`` routes. See web/launcher.py
# for the rationale (browser-console 404s on multi-page navigation).
CMD ["python", "web/launcher.py"]
