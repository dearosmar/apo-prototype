import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.config import get_settings

FALLBACK_MESSAGE = (
    "[폴백] ANTHROPIC_API_KEY가 없어 Claude를 호출하지 않았습니다. "
    "backend/.env에 키를 넣으면 실제 응답이 나옵니다. 데모는 폴백 모드로도 진행 가능."
)


def main() -> int:
    api_key = os.environ.get("ANTHROPIC_API_KEY") or get_settings().anthropic_api_key
    if not api_key:
        print(FALLBACK_MESSAGE)
        return 0

    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    try:
        response = client.messages.create(
            model="claude-opus-5",
            max_tokens=256,
            messages=[
                {
                    "role": "user",
                    "content": "수입 소상공인을 돕는 AI '바다 건너 사장님'의 개발이 시작됐어. 한국어 한 문장으로 응원해 줘.",
                }
            ],
        )
    except anthropic.AuthenticationError:
        print("[오류] API 키가 유효하지 않습니다. backend/.env의 ANTHROPIC_API_KEY를 확인하세요.")
        return 1
    except anthropic.APIConnectionError:
        print("[오류] 네트워크 오류로 Claude에 연결하지 못했습니다.")
        print(FALLBACK_MESSAGE)
        return 1

    if response.stop_reason == "refusal":
        print("[폴백] Claude가 응답을 거절했습니다. 프롬프트를 확인하세요.")
        return 0

    text = next((b.text for b in response.content if b.type == "text"), "")
    print(f"Claude: {text}")
    print(f"(model={response.model}, in={response.usage.input_tokens}tok, out={response.usage.output_tokens}tok)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
