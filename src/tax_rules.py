from decimal import Decimal
from numbers import Integral

TAX_RATES = {
    "INTEREST": 14,
    "BUSINESS": 3,
    "OTHER": 20
}

SUBTYPES = {
    "INTEREST": "BANK_DEPOSIT",
    "BUSINESS": "RECURRING_SERVICE",
    "OTHER": "ONE_TIME_LECTURE"
}


class ReviewRequired(ValueError):
    pass


def truncate_10(amount):
    return int((amount // 10) * 10)


def calculate_tax(
    income_type,
    gross_amount,
    residency="RESIDENT",
    income_subtype=None
):

    if isinstance(gross_amount, bool) or not isinstance(
        gross_amount, Integral
    ):
        raise ValueError("지급액은 정수여야 합니다.")

    if gross_amount <= 0:
        raise ValueError("지급액은 양수여야 합니다.")

    if residency != "RESIDENT":
        raise ReviewRequired("거주자 여부 추가 검토 필요")

    if income_type not in TAX_RATES:
        raise ReviewRequired("지원하지 않는 소득 유형")

    if income_subtype != SUBTYPES[income_type]:
        raise ReviewRequired("지원하지 않는 세부 소득 유형")

    gross = Decimal(int(gross_amount))
    expense = Decimal("0")
    reason = "일반 원천징수"

    if income_type == "OTHER":

        # 원 미만 필요경비 발생 건은 MVP 검토 대상으로 분리
        if gross_amount % 5 != 0:
            raise ReviewRequired("필요경비 원 미만 단수 처리 확인")

        expense = gross * Decimal("0.60")

    tax_base = gross - expense

    if income_type == "OTHER" and tax_base <= 50000:
        raw_tax = Decimal("0")
        reason = "기타소득 과세최저한"

    else:
        rate = Decimal(TAX_RATES[income_type]) / 100
        raw_tax = tax_base * rate

        if income_type in ["INTEREST", "BUSINESS"] and raw_tax < 1000:
            reason = "소액부징수 적용 제외"

    # 학습용 가정: 지급 건별 10원 미만 절사
    income_tax = truncate_10(raw_tax)
    local_tax = truncate_10(Decimal(income_tax) / 10)

    total_tax = income_tax + local_tax
    net_amount = int(gross) - total_tax

    return {
        "gross_amount": int(gross),
        "expense_amount": int(expense),
        "tax_base": int(tax_base),
        "income_tax": income_tax,
        "local_tax": local_tax,
        "total_tax": total_tax,
        "net_amount": net_amount,
        "reason": reason
    }
