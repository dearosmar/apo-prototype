import re
from typing import Dict, List, Optional

from app.config import BACKEND_DIR

SAMPLES_DIR = BACKEND_DIR / "data" / "samples"
SAMPLES = {
    "normal": ("pi_normal_cn.txt", "정상 PI 샘플 (FOB · 선금 30%)"),
    "risky": ("pi_risky_cn.txt", "위험 PI 샘플 (EXW · 100% 선지급 · 개인계좌)"),
}

INCOTERMS = ("FOB", "CIF", "CFR", "EXW", "DDP", "DAP", "FCA")

DEPOSIT_RE = re.compile(r"(\d{1,3})\s*%\s*(?:T/T)?\s*(?:deposit|定金|预付|선금|advance)", re.I)
FULL_ADVANCE_RE = re.compile(r"100\s*%|全款预付|全额预付", re.I)
QTY_RE = re.compile(r"(?:Quantity|数量)[^\d]*([\d,]+)\s*(?:PCS|pcs|个|EA)", re.I)
UNIT_PRICE_RE = re.compile(r"(?:Unit\s*Price|单价)[^\d]*(?:CNY|USD|RMB)?\s*([\d,]+\.?\d*)", re.I)
TOTAL_RE = re.compile(r"(?:Total\s*Amount|总金额)[^\d]*(?:CNY|USD|RMB)?\s*([\d,]+\.?\d*)", re.I)
LEAD_RE = re.compile(r"(?:Lead\s*Time|交货期|납기)[^\n]*?(\d+)\s*(?:days|天|일)", re.I)
PERSONAL_ACCT_RE = re.compile(r"personal|个人账户|个人帐户", re.I)
PAYMENT_LINE_RE = re.compile(r"(?:Payment\s*Terms|付款方式)\s*[::]?\s*([^\n]+)", re.I)
ACCOUNT_NAME_RE = re.compile(r"(?:Account\s*Name|账户名)\s*[::]?\s*([^\n]+)", re.I)


def extract_text(filename: str, data: bytes) -> Optional[str]:
    name = filename.lower()
    if name.endswith(".txt"):
        return data.decode("utf-8", errors="ignore")
    if name.endswith(".pdf"):
        import io

        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    return None


def parse_fields(text: str) -> Dict:
    deposit = DEPOSIT_RE.search(text)
    payment_line = PAYMENT_LINE_RE.search(text)
    incoterm = next((t for t in INCOTERMS if re.search(rf"\b{t}\b", text)), None)
    lead = LEAD_RE.search(text)
    qty = QTY_RE.search(text)
    unit_price = UNIT_PRICE_RE.search(text)
    total = TOTAL_RE.search(text)
    account_name = ACCOUNT_NAME_RE.search(text)

    deposit_pct: Optional[int] = None
    if FULL_ADVANCE_RE.search(text):
        deposit_pct = 100
    elif deposit:
        deposit_pct = int(deposit.group(1))

    return {
        "payment_terms": payment_line.group(1).strip() if payment_line else None,
        "deposit_pct": deposit_pct,
        "incoterms": incoterm,
        "lead_time_days": int(lead.group(1)) if lead else None,
        "quantity": int(qty.group(1).replace(",", "")) if qty else None,
        "unit_price": float(unit_price.group(1).replace(",", "")) if unit_price else None,
        "total_amount": float(total.group(1).replace(",", "")) if total else None,
        "beneficiary": account_name.group(1).strip() if account_name else None,
        "personal_account": bool(PERSONAL_ACCT_RE.search(text)),
    }


def run_checks(fields: Dict) -> List[Dict]:
    checks: List[Dict] = []

    deposit = fields["deposit_pct"]
    if fields["payment_terms"] is None:
        checks.append({"item": "결제조건", "status": "red", "finding": "결제조건이 문서에 없어요", "basis": "지급 조건 미기재 시 분쟁 시 근거가 없어요"})
    elif deposit == 100:
        checks.append({"item": "결제조건", "status": "red", "finding": "100% 선지급(全款预付) 조건이에요", "basis": "물건을 받기 전 전액 송금은 미선적 사기의 전형적 패턴이에요"})
    elif deposit is not None and deposit > 50:
        checks.append({"item": "결제조건", "status": "yellow", "finding": f"선금 비율이 {deposit}%로 높아요", "basis": "통상 선금 30% 내외가 일반적이에요"})
    else:
        checks.append({"item": "결제조건", "status": "green", "finding": f"선금 {deposit}% + 잔금 구조예요" if deposit is not None else "결제조건이 명시돼 있어요", "basis": "선금 30% 내외는 통상적인 조건이에요"})

    incoterm = fields["incoterms"]
    if incoterm is None:
        checks.append({"item": "인코텀즈", "status": "yellow", "finding": "거래조건(FOB/CIF 등)이 없어요", "basis": "운임·위험 부담 주체가 불명확하면 추가 비용 분쟁이 생겨요"})
    elif incoterm == "EXW":
        checks.append({"item": "인코텀즈", "status": "yellow", "finding": "EXW(공장 인도) 조건이에요", "basis": "중국 내륙 운송·수출통관까지 구매자 부담이라 초보 수입자에게 불리해요"})
    else:
        checks.append({"item": "인코텀즈", "status": "green", "finding": f"{incoterm} 조건이 명시돼 있어요", "basis": "운임·위험 분기점이 명확해요"})

    if fields["lead_time_days"] is None:
        checks.append({"item": "납기", "status": "yellow", "finding": "납기(교화기)가 없어요", "basis": "납기 미기재 시 지연에 대응할 근거가 없어요"})
    else:
        checks.append({"item": "납기", "status": "green", "finding": f"납기 {fields['lead_time_days']}일이 명시돼 있어요", "basis": "지연 시 협상 근거가 돼요"})

    if fields["quantity"] and fields["unit_price"] and fields["total_amount"]:
        expected = round(fields["quantity"] * fields["unit_price"], 2)
        if abs(expected - fields["total_amount"]) < 0.01:
            checks.append({"item": "수량·금액", "status": "green", "finding": "수량×단가와 총액이 일치해요", "basis": f"{fields['quantity']} × {fields['unit_price']} = {expected}"})
        else:
            checks.append({"item": "수량·금액", "status": "red", "finding": "수량×단가와 총액이 달라요", "basis": f"계산값 {expected} ≠ 표기 총액 {fields['total_amount']}"})
    else:
        checks.append({"item": "수량·금액", "status": "yellow", "finding": "수량·단가·총액 중 빠진 항목이 있어요", "basis": "금액 근거가 불완전해요"})

    if fields["personal_account"]:
        checks.append({"item": "수취 계좌", "status": "red", "finding": "개인 명의 계좌로 송금을 요구해요", "basis": "회사 거래에서 개인계좌 수취는 대표적인 사기 신호예요"})
    elif fields["beneficiary"]:
        checks.append({"item": "수취 계좌", "status": "green", "finding": "회사 명의 계좌예요", "basis": f"수취인: {fields['beneficiary']}"})
    else:
        checks.append({"item": "수취 계좌", "status": "yellow", "finding": "수취 계좌 정보가 없어요", "basis": "송금 전 반드시 계좌 명의를 확인해야 해요"})

    return checks


def overall_status(checks: List[Dict]) -> str:
    statuses = {c["status"] for c in checks}
    if "red" in statuses:
        return "red"
    if "yellow" in statuses:
        return "yellow"
    return "green"


def load_sample(name: str) -> Dict:
    filename, label = SAMPLES[name]
    text = (SAMPLES_DIR / filename).read_text(encoding="utf-8")
    return {"filename": filename, "label": label, "text": text}
