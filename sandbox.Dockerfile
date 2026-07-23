FROM python:3.12-slim

RUN pip install --no-cache-dir \
    numpy pandas matplotlib scipy pillow \
    requests httpx openpyxl xlrd \
    sympy statistics more-itertools \
    && rm -rf /root/.cache/pip

# UID/GID 65534 já existem como nobody/nogroup em python:3.12-slim (achado
# 2026-07-23, base image mudou desde a 1a versão deste Dockerfile) — não precisa
# criar usuário novo, só usar o que já existe.
WORKDIR /sandbox

USER 65534:65534
