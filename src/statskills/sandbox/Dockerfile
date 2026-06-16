# Pinned sandbox execution image for statskills (ROADMAP §7).
#
# Build:  make sandbox-image            (tags statskills-sandbox:0.1.0)
# Runtime: the image runs sandbox/driver.py as a stateful IPython kernel reading a
# JSON-lines protocol on stdin/stdout. The DockerExecutor launches it with
# `docker run -i --network none --memory ... --user ... -v <task>:/work`.
FROM python:3.13-slim

RUN useradd --create-home --uid 1000 sandbox

COPY requirements.txt /opt/requirements.txt
RUN pip install --no-cache-dir -r /opt/requirements.txt

COPY driver.py /opt/kernel_driver.py

# Writable scratch owned by the non-root sandbox user (uid 1000 == the
# DockerExecutor --user). Datasets are bind-mounted here read-only at run time.
RUN mkdir -p /work && chown 1000:1000 /work

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER sandbox
WORKDIR /work
CMD ["python", "/opt/kernel_driver.py"]
