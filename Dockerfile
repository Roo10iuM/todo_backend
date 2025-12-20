FROM python:3.13 AS requirements-stage
WORKDIR /tmp
RUN pip install --upgrade "poetry==2.1.2" "poetry-plugin-export"
COPY ./pyproject.toml ./poetry.lock* /tmp/
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

FROM python:3.13
WORKDIR /code
COPY --from=requirements-stage /tmp/requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
COPY ./src /code/src
CMD ["python", "src/main.py"]