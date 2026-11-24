from pathlib import Path
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

# 수기로 계산한 정상 거래 사례
# 소득유형, 세부유형, 지급액, 필요경비, 소득세, 지방소득세

FIXTURES = [
    ("INTEREST", "BANK_DEPOSIT", 1000000, 0, 140000, 14000),
    ("INTEREST", "BANK_DEPOSIT", 5000, 0, 700, 70),
    ("INTEREST", "BANK_DEPOSIT", 200000, 0, 28000, 2800),
    ("INTEREST", "BANK_DEPOSIT", 500000, 0, 70000, 7000),
    ("BUSINESS", "RECURRING_SERVICE", 1000000, 0, 30000, 3000),
    ("BUSINESS", "RECURRING_SERVICE", 30000, 0, 900, 90),
    ("BUSINESS", "RECURRING_SERVICE", 800000, 0, 24000, 2400),
    ("BUSINESS", "RECURRING_SERVICE", 2000000, 0, 60000, 6000),
    ("OTHER", "ONE_TIME_LECTURE", 125000, 75000, 0, 0),
    ("OTHER", "ONE_TIME_LECTURE", 125005, 75003, 10000, 1000),
    ("OTHER", "ONE_TIME_LECTURE", 500000, 300000, 40000, 4000),
    ("OTHER", "ONE_TIME_LECTURE", 1000000, 600000, 80000, 8000)
]

DETAIL_COLUMNS = [
    "payment_id",
    "recipient_id",
    "income_type",
    "accrual_month",
    "payment_date",
    "gross_amount",
    "income_tax",
    "local_tax"
]


def make_summary(details):
    return (
        details.groupby("income_type", as_index=False)
        .agg(
            payment_count=("payment_id", "size"),
            gross_amount=("gross_amount", "sum"),
            income_tax=("income_tax", "sum"),
            local_tax=("local_tax", "sum")
        )
    )


def generate_data(seed=42):

    DATA_DIR.mkdir(exist_ok=True)

    rng = np.random.default_rng(seed)
    rows = []

    fixed_indices = [0, 4, 10, 2, 4, 6, 8, 5, 11, 3, 0, 4]

    for i in range(199):

        fixture_index = (
            fixed_indices[i]
            if i < len(fixed_indices)
            else int(rng.integers(0, len(FIXTURES)))
        )

        kind, subtype, gross, expense, tax, local = (
            FIXTURES[fixture_index]
        )

        rows.append({
            "row_id": f"R{i + 1:03d}",
            "payment_id": f"P{i + 1:03d}",
            "recipient_id": f"C{rng.integers(1, 101):03d}",
            "residency": "RESIDENT",
            "income_type": kind,
            "income_subtype": subtype,
            "accrual_month": "2026-10",
            "payment_date": f"2026-10-{rng.integers(1, 32):02d}",
            "gross_amount": gross,
            "expense_amount": expense,
            "income_tax": tax,
            "local_tax": local,
            "net_amount": gross - tax - local
        })

    clean = pd.DataFrame(rows)
    payments = clean.copy()

    # 세액 오류 삽입
    payments.loc[4, "income_tax"] += 1000
    payments.loc[4, "net_amount"] -= 1000

    payments.loc[5, "local_tax"] += 100
    payments.loc[5, "net_amount"] -= 100

    payments.loc[6, "income_tax"] = 10000
    payments.loc[6, "net_amount"] -= 10000

    payments.loc[7, ["income_tax", "local_tax"]] = 0
    payments.loc[7, "net_amount"] = payments.loc[7, "gross_amount"]

    payments.loc[8, "net_amount"] += 500

    # 공통 가상 지급 기록을 기반으로 별도 신고자료 구성
    details = payments[DETAIL_COLUMNS].copy()
    summary = make_summary(details)

    # 원장 데이터 오류
    payments.loc[0, "recipient_id"] = ""
    payments.loc[1, "gross_amount"] = -100000
    payments.loc[2, "payment_date"] = "2026-10-32"
    payments.loc[3, "residency"] = "NON_RESIDENT"

    # 중복 거래 삽입
    duplicate = payments.iloc[[9]].copy()
    duplicate.loc[:, "row_id"] = "R200"

    payments = pd.concat(
        [payments, duplicate],
        ignore_index=True
    )

    # 신고자료 누락
    details = details[details["payment_id"] != "P011"].copy()

    # 신고자료 금액 불일치
    details.loc[
        details["payment_id"] == "P012",
        "gross_amount"
    ] += 10000

    # 신고자료에만 존재하는 거래
    extra = details.iloc[[6]].copy()

    extra.loc[:, "payment_id"] = "P999"
    extra.loc[:, "recipient_id"] = "C999"

    details = pd.concat([details, extra], ignore_index=True)

    # 오류 정답표: 검증 함수와 독립적으로 지정
    truth = [
        ("PAYMENT", "R001", "DATA-01"),
        ("PAYMENT", "R002", "DATA-03"),
        ("PAYMENT", "R003", "DATA-04"),
        ("PAYMENT", "R004", "TAX-01"),
        ("PAYMENT", "R005", "TAX-02"),
        ("PAYMENT", "R006", "TAX-03"),
        ("PAYMENT", "R007", "TAX-02"),
        ("PAYMENT", "R007", "TAX-04"),
        ("PAYMENT", "R008", "TAX-02"),
        ("PAYMENT", "R008", "TAX-03"),
        ("PAYMENT", "R008", "TAX-05"),
        ("PAYMENT", "R009", "TAX-06"),
        ("PAYMENT", "R010", "DATA-02"),
        ("PAYMENT", "R200", "DATA-02"),
        ("DETAIL", "P011", "REC-01"),
        ("DETAIL", "P012", "REC-03"),
        ("DETAIL", "P999", "REC-02"),
        ("SUMMARY", "INTEREST", "REC-04"),
        ("SUMMARY", "BUSINESS", "REC-04"),
        ("SUMMARY", "OTHER", "REC-04")
    ]

    truth = pd.DataFrame(
        truth,
        columns=["scope", "key", "code"]
    )

    for filename, frame in [
        ("payments.csv", payments),
        ("filing_details.csv", details),
        ("filing_summary.csv", summary),
        ("ground_truth.csv", truth)
    ]:
        frame.to_csv(
            DATA_DIR / filename,
            index=False,
            encoding="utf-8-sig"
        )

    return payments, details, summary, truth


if __name__ == "__main__":
    payments, details, summary, truth = generate_data()
    print("지급자료:", len(payments))
    print("신고 기초자료:", len(details))
    print("정답표 검증 항목:", len(truth))
