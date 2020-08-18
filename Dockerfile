FROM python:3.7-slim

COPY windtunnel.py windtunnel.py
EXPOSE 5005/udp
EXPOSE 12321/tcp
ENTRYPOINT ["./windtunnel.py"]
