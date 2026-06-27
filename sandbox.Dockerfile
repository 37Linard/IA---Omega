FROM python:3.12-slim

RUN pip install --no-cache-dir \
    numpy pandas matplotlib scipy pillow \
    requests httpx openpyxl xlrd \
    sympy statistics more-itertools \
    && rm -rf /root/.cache/pip

RUN groupadd -g 65534 sandbox && useradd -u 65534 -g sandbox -s /bin/sh -d /sandbox sandbox

WORKDIR /sandbox

USER 65534:65534
