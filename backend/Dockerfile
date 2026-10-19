FROM python:3.12-slim

# HuggingFace Spaces exige uid 1000 y puerto 7860.
# La API es ligera: FFmpeg, Kokoro y torch viven solo en el workflow de GitHub Actions.
RUN useradd -m -u 1000 user
USER user
ENV PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1
WORKDIR /home/user/app

COPY --chown=user pyproject.toml ./
COPY --chown=user app ./app
RUN pip install --no-cache-dir .

EXPOSE 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
