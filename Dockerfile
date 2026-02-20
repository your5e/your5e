FROM python:3.14-slim

WORKDIR /app

RUN pip install --upgrade pip

COPY pyproject.toml .
RUN pip install -e ".[dev]"

COPY . .

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
