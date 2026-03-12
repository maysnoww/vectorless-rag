import os
import subprocess
import sys
from importlib.util import find_spec
from pathlib import Path


def load_dotenv(project_dir):
    env_file = project_dir / ".env"
    if not env_file.exists():
        return

    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if value and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]

        os.environ.setdefault(key, value)


def ensure_dependencies(project_dir):
    requirements_file = project_dir / "requirements.txt"

    if find_spec("aiohttp") is not None and find_spec("certifi") is not None:
        return

    if not requirements_file.exists():
        raise RuntimeError("Missing requirements.txt; cannot auto-install dependencies.")

    print("[SETUP] Missing dependencies detected. Installing from requirements.txt...")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)]
    )

    if find_spec("aiohttp") is None or find_spec("certifi") is None:
        raise RuntimeError(
            "Dependency installation finished, but required packages are still unavailable."
        )


def run():
    project_dir = Path(__file__).resolve().parent
    os.chdir(project_dir)
    load_dotenv(project_dir)
    ensure_dependencies(project_dir)

    from main import main

    return main()


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\nBye!")
        sys.exit(130)
    except Exception as exc:
        print(f"\n[ERR] {exc}")
        sys.exit(1)
