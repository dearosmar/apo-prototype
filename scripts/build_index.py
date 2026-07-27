import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.services import rag


def main() -> int:
    if not rag.DOCS_DIR.exists():
        print(f"[오류] 문서 폴더가 없습니다: {rag.DOCS_DIR}")
        return 1
    started = time.time()
    count = rag.build_index()
    print(f"인덱스 생성 완료: 청크 {count}개 → {rag.VECTORSTORE_DIR} ({time.time() - started:.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
