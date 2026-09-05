# 로컬과 CI에서 동일한 검증을 실행하고 실패 시 즉시 중단한다.
import subprocess
import sys
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent
    for args in (("ruff", "check", "."), ("pytest",)):
        result = subprocess.run([sys.executable, "-m", *args], cwd=root)
        if result.returncode:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
