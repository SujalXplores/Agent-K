# The deployer sidecar - sole holder of the Docker socket (LAW2-03).
#
# Needs the docker CLI *and* the compose plugin available inside the image, since
# it shells out to `docker compose up -d --force-recreate`. The socket itself is
# mounted at run time (see docker-compose.yaml), never baked in here.
FROM python:3.12-slim

# docker-cli + docker-compose-plugin from Docker's official apt repo. `docker.io`
# from Debian's own repo would pull the full daemon (which this container must
# never run - it talks to the HOST's daemon through the mounted socket).
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gnupg \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && chmod a+r /etc/apt/keyrings/docker.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
        > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /srv

COPY deployer/requirements.txt /srv/deployer/requirements.txt
RUN pip install --no-cache-dir -r /srv/deployer/requirements.txt

COPY deployer/ /srv/deployer/

EXPOSE 9000

CMD ["uvicorn", "deployer.main:app", "--host", "0.0.0.0", "--port", "9000"]
