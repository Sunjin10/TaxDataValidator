from datetime import date
from decimal import Decimal, InvalidOperation

import pandas as pd

from src.tax_rules import calculate_tax, ReviewRequired

TARGET_MONTH = "2026-10"

REQUIRED = [
    "row_id",
    "payment_id",
    "recipient_id",
    "residency",
    "income_type",
    "income_subtype",
    "accrual_month",
    "payment_date",
    "gross_amount",
    "expense_amount",
    "income_tax",
    "local_tax",
    "net_amount"
]

AMOUNT_COLUMNS = [
    "gross_amount",
    "expense_amount",
    "income_tax",
    "local_tax",
    "net_amount"
]

EVENT_COLUMNS = [
    "scope", "key", "code", "status",
    "message", "expected", "actual"
]


def is_missing(value):
    return bool(pd.isna(value)) or str(value).strip() == ""


def as_integer(value):
    try:
        number = Decimal(str(value))

        if not number.is_finite():
            return None

        if number != number.to_integral_value():
            return None

        return int(number)

    except (InvalidOperation, ValueError, TypeError):
        return None


def event(scope, key, code, message,
          status="ERROR", expected=None, actual=None):

    return {
        "scope": scope,
        "key": key,
        "code": code,
        "status": status,
        "message": message,
        "expected": expected,
        "actual": actual
    }


def validate_payments(df):

    absent = set(REQUIRED) - set(df.columns)

    if absent:
        raise ValueError(f"필수 컬럼 누락: {sorted(absent)}")

    transactions = []
    events = []

    duplicate_mask = df["payment_id"].duplicated(keep=False)
    duplicate_rows = df["row_id"].duplicated(keep=False)

    for pos, (_, row) in enumerate(df.iterrows()):

        record = row.to_dict()
        key = str(row["row_id"]) if not is_missing(
            row["row_id"]
        ) else f"ROW_{pos + 1}"

        issues = []

        def add(code, message, status="ERROR",
                expected=None, actual=None):

            issues.append(
                event(
                    "PAYMENT", key, code, message,
                    status, expected, actual
                )
            )

        # DATA-01: 필수값 누락
        missing = [
            col for col in REQUIRED
            if is_missing(row[col])
        ]

        if missing:
            add("DATA-01", "필수값 누락: " + ", ".join(missing))

        # DATA-02: 거래 ID 또는 행 ID 중복
        if duplicate_mask.iloc[pos] or duplicate_rows.iloc[pos]:
            add("DATA-02", "거래 식별번호 중복")

        # DATA-03: 금액 오류
        amounts = {}

        for col in AMOUNT_COLUMNS:

            if is_missing(row[col]):
                continue

            value = as_integer(row[col])

            if (
                value is None
                or value < 0
                or (col == "gross_amount" and value == 0)
            ):
                add(
                    "DATA-03",
                    f"잘못된 금액: {col}",
                    actual=str(row[col])
                )
            else:
                amounts[col] = value

        # DATA-04: 날짜 검증
        if not is_missing(row["payment_date"]):

            try:
                payment_date = date.fromisoformat(
                    str(row["payment_date"])
                )

                if payment_date.strftime("%Y-%m") != TARGET_MONTH:
                    add("DATA-04", "신고 대상 지급월 불일치")

            except ValueError:
                add("DATA-04", "유효하지 않은 지급일자")

        if not is_missing(row["accrual_month"]):
            try:
                month = str(row["accrual_month"])
                parsed = date.fromisoformat(month + "-01")

                if parsed.strftime("%Y-%m") != month:
                    raise ValueError

            except ValueError:
                add("DATA-04", "유효하지 않은 귀속연월")

        structural_error = any(
            issue["code"].startswith("DATA")
            for issue in issues
        )

        record["reconciliation_eligible"] = not structural_error
        record["tax_calculated"] = False

        for col in [
            "expected_income_tax",
            "expected_local_tax",
            "expected_expense_amount",
            "income_tax_diff",
            "local_tax_diff",
            "expected_net_amount"
        ]:
            record[col] = None

        if not structural_error:

            gross = amounts["gross_amount"]
            recorded_tax = amounts["income_tax"]
            recorded_local = amounts["local_tax"]

            # TAX-06: 실지급액 대사
            expected_net = gross - recorded_tax - recorded_local

            if (
                amounts["net_amount"] != expected_net
                or expected_net < 0
            ):
                add(
                    "TAX-06",
                    "실지급액과 기록 세액 불일치",
                    expected=expected_net,
                    actual=amounts["net_amount"]
                )

            try:
                result = calculate_tax(
                    row["income_type"],
                    gross,
                    row["residency"],
                    row["income_subtype"]
                )

                expected_tax = result["income_tax"]
                expected_local = result["local_tax"]

                record.update({
                    "tax_calculated": True,
                    "expected_income_tax": expected_tax,
                    "expected_local_tax": expected_local,
                    "expected_expense_amount": result["expense_amount"],
                    "income_tax_diff": recorded_tax - expected_tax,
                    "local_tax_diff": recorded_local - expected_local,
                    "expected_net_amount": result["net_amount"],
                    "tax_reason": result["reason"]
                })

                # TAX-02: 소득세 불일치
                if recorded_tax != expected_tax:
                    add(
                        "TAX-02", "소득세 불일치",
                        expected=expected_tax,
                        actual=recorded_tax
                    )

                # TAX-03: 지방소득세 불일치
                if recorded_local != expected_local:
                    add(
                        "TAX-03", "지방소득세 불일치",
                        expected=expected_local,
                        actual=recorded_local
                    )

                # TAX-04: 과세최저한 미적용
                if (
                    result["reason"] == "기타소득 과세최저한"
                    and (recorded_tax > 0 or recorded_local > 0)
                ):
                    add("TAX-04", "기타소득 과세최저한 미적용")

                # TAX-05: 소액부징수 예외 미반영
                if (
                    result["reason"] == "소액부징수 적용 제외"
                    and expected_tax > 0
                    and recorded_tax == 0
                ):
                    add("TAX-05", "소액부징수 적용 제외 규정 확인")

                # TAX-07: 필요경비 검토
                if amounts["expense_amount"] != result["expense_amount"]:
                    add(
                        "TAX-07",
                        "필요경비 적용 근거 추가 확인",
                        status="REVIEW",
                        expected=result["expense_amount"],
                        actual=amounts["expense_amount"]
                    )

                    # 필요경비가 다르면 확정 세액 차이에서 제외
                    record["tax_calculated"] = False
                    record["income_tax_diff"] = None
                    record["local_tax_diff"] = None

                    for issue in issues:
                        if issue["code"] in [
                            "TAX-02", "TAX-03", "TAX-04"
                        ]:
                            issue["status"] = "REVIEW"

            except ReviewRequired as exc:
                add("TAX-01", str(exc), status="REVIEW")

        statuses = [issue["status"] for issue in issues]

        if "ERROR" in statuses:
            record["status"] = "ERROR"
        elif "REVIEW" in statuses:
            record["status"] = "REVIEW"
        else:
            record["status"] = "PASS"

        record["error_codes"] = ", ".join(
            sorted({issue["code"] for issue in issues})
        )

        transactions.append(record)
        events.extend(issues)

    return (
        pd.DataFrame(transactions),
        pd.DataFrame(events, columns=EVENT_COLUMNS)
    )
