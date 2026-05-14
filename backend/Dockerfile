FROM python:3.11-slim

RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

WORKDIR /app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy model
RUN python -m spacy download en_core_web_sm

COPY --chown=user . .

CMD ["sh", "-c", "python manage.py migrate && gunicorn ats_checker.wsgi --bind 0.0.0.0:7860 --workers 2 --timeout 120"]