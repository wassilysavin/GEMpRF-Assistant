import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from gemprf_assistant.evaluation import main


if __name__ == "__main__":
    main()
