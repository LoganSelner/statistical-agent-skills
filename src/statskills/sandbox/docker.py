"""Docker-backed executor — the secure default (ROADMAP §7).

Runs the sandbox driver inside a fresh, network-isolated container per session
(``docker run -i --network none`` with memory/cpu/pid limits, non-root). If
Docker is unavailable or the image is missing, construction raises
:class:`DockerError` — there is **no silent fallback to local execution**.
"""

from __future__ import annotations

from collections.abc import Mapping
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid

from statskills.sandbox.base import Session
from statskills.sandbox.session import SubprocessSession

DEFAULT_IMAGE = "statskills-sandbox:0.1.0"
# Fixed non-root UID the sandbox runs as. Matches the `sandbox` user and the chown
# of /work in the image Dockerfile, so model code never runs as root — even when
# the harness itself runs as root (CI / devcontainers).
_SANDBOX_UID = 1000


class DockerError(RuntimeError):
    """Docker is unavailable or misconfigured. The harness never falls back."""


class DockerExecutor:
    """Runs each session in a fresh, isolated container of a pinned image."""

    def __init__(
        self,
        image: str = DEFAULT_IMAGE,
        *,
        timeout: float = 30.0,
        memory: str = "2g",
        cpus: str = "2",
        pids_limit: int = 256,
    ) -> None:
        self._image = image
        self._timeout = timeout
        self._memory = memory
        self._cpus = cpus
        self._pids_limit = pids_limit
        self._preflight()

    def _preflight(self) -> None:
        try:
            subprocess.run(
                ["docker", "version", "--format", "{{.Server.Version}}"],
                check=True,
                capture_output=True,
                text=True,
                timeout=15,
            )
        except FileNotFoundError as e:
            raise DockerError("docker CLI not found on PATH.") from e
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            raise DockerError(
                "Docker daemon is not reachable. Start Docker and retry — the "
                "harness does not fall back to local execution."
            ) from e
        if (
            subprocess.run(
                ["docker", "image", "inspect", self._image],
                capture_output=True,
                text=True,
            ).returncode
            != 0
        ):
            raise DockerError(
                f"Sandbox image '{self._image}' not found. Build it with "
                "`make sandbox-image`."
            )

    @property
    def image_digest(self) -> str:
        """The image content id (sha256) — recorded in provenance (ROADMAP §9)."""
        out = subprocess.run(
            ["docker", "image", "inspect", "--format", "{{.Id}}", self._image],
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip()

    def start(
        self,
        datasets: tuple[Path, ...] = (),
        *,
        skills: Mapping[str, str] | None = None,
    ) -> Session:
        # Stage read-only copies of the datasets on the host, then bind-mount each
        # into the working dir read-only — cell code can read them but never
        # overwrite them (which would corrupt later cells in the same stateful
        # task). Scratch is the image's writable, sandbox-owned /work, so nothing
        # writable on the host is exposed.
        staging = tempfile.mkdtemp(prefix="statskills-docker-")
        mounts: list[str] = []
        for ds in datasets:
            dest = Path(staging) / ds.name
            shutil.copy(ds, dest)
            os.chmod(dest, 0o644)  # world-readable for the sandbox UID
            mounts += ["-v", f"{dest}:/work/{ds.name}:ro"]

        # Skill files the agent may read on demand, staged read-only under skills/.
        if skills:
            skills_dir = Path(staging) / "skills"
            skills_dir.mkdir()
            for filename, content in skills.items():
                dest = skills_dir / filename
                dest.write_text(content)
                os.chmod(dest, 0o644)
            mounts += ["-v", f"{skills_dir}:/work/skills:ro"]

        name = f"statskills-{uuid.uuid4().hex[:12]}"
        command = [
            "docker",
            "run",
            "-i",
            "--rm",
            "--name",
            name,
            "--network",
            "none",
            "--memory",
            self._memory,
            "--memory-swap",
            self._memory,
            "--cpus",
            self._cpus,
            "--pids-limit",
            str(self._pids_limit),
            "--user",
            f"{_SANDBOX_UID}:{_SANDBOX_UID}",
            "-e",
            "HOME=/work",
            *mounts,
            "-w",
            "/work",
            self._image,
            "python",
            "/opt/kernel_driver.py",
        ]

        def terminate() -> None:
            subprocess.run(["docker", "kill", name], capture_output=True, text=True)

        return SubprocessSession(
            command,
            timeout=self._timeout,
            cwd=None,
            terminate=terminate,
            cleanup_dir=staging,
        )
