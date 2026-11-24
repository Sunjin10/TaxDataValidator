import pandas as pd

from src.generate_data import DETAIL_COLUMNS, make_summary
from src.validator import as_integer, is_missing, event, EVENT_COLUMNS

COMPARE_COLUMNS = [
    col for col in DETAIL_COLUMNS if col != "payment_id"
]

DETAIL_AMOUNTS = [
    "gross_amount", "income_tax", "local_tax"
]

SUMMARY_COLUMNS = [
    "payment_count", "gross_amount", "income_tax", "local_tax"
]


def reconcile(transactions, details, summary):

    events = []
    detail_results = []
    summary_results = []

    if set(DETAIL_COLUMNS) - set(details.columns):
        raise ValueError("신고 기초자료 필수 컬럼 누락")

    if set(["income_type"] + SUMMARY_COLUMNS) - set(summary.columns):
        raise ValueError("집계자료 필수 컬럼 누락")

    details = details.copy()

    blocked_ids = set(
        transactions.loc[
            ~transactions["reconciliation_eligible"],
            "payment_id"
        ]
    )

    duplicate_mask = details["payment_id"].duplicated(keep=False)
    invalid_positions = set()

    # 신고 기초자료 자체의 정합성 검증
    for pos, (_, row) in enumerate(details.iterrows()):

        key = str(row["payment_id"])

        if any(is_missing(row[col]) for col in DETAIL_COLUMNS):

            events.append(event(
                "DETAIL", key, "DATA-01", "신고자료 필수값 누락"
            ))

            invalid_positions.add(pos)

        if duplicate_mask.iloc[pos]:

            events.append(event(
                "DETAIL", key, "DATA-02", "신고자료 거래 중복"
            ))

            invalid_positions.add(pos)

        invalid_amounts = [
            col for col in DETAIL_AMOUNTS
            if as_integer(row[col]) is None
            or as_integer(row[col]) < 0
            or (
                col == "gross_amount"
                and as_integer(row[col]) == 0
            )
        ]

        if invalid_amounts:

            events.append(event(
                "DETAIL", key, "DATA-03",
                "신고자료 금액 오류: " + ", ".join(invalid_amounts)
            ))

            invalid_positions.add(pos)

    if invalid_positions:
        blocked_ids.update(
            details.iloc[sorted(invalid_positions)]["payment_id"]
        )

    for key in sorted(map(str, blocked_ids)):
        detail_results.append({
            "payment_id": key,
            "status": "BLOCKED",
            "message": "원장 또는 신고자료의 정합성 오류로 대사 보류"
        })

    left = transactions.loc[
        transactions["reconciliation_eligible"]
        & ~transactions["payment_id"].isin(blocked_ids),
        DETAIL_COLUMNS
    ].copy()

    right = details.loc[
        ~details["payment_id"].isin(blocked_ids),
        DETAIL_COLUMNS
    ].copy()

    for col in DETAIL_AMOUNTS:
        left[col] = left[col].map(as_integer)
        right[col] = right[col].map(as_integer)

    merged = left.merge(
        right,
        on="payment_id",
        how="outer",
        suffixes=("_ledger", "_filing"),
        indicator=True,
        validate="one_to_one"
    )

    for _, row in merged.iterrows():

        key = row["payment_id"]
        record = row.to_dict()

        if row["_merge"] == "left_only":

            code = "REC-01"
            message = "신고 기초자료 누락"

        elif row["_merge"] == "right_only":

            code = "REC-02"
            message = "지급 원장에 없는 신고자료"

        else:

            differences = [
                col for col in COMPARE_COLUMNS
                if row[f"{col}_ledger"] != row[f"{col}_filing"]
            ]

            if differences:
                code = "REC-03"
                message = "거래 불일치: " + ", ".join(differences)
            else:
                code = None
                message = "대사 일치"

        record["status"] = "ERROR" if code else "PASS"
        record["code"] = code
        record["message"] = message

        detail_results.append(record)

        if code:
            events.append(event(
                "DETAIL", key, code, message
            ))

    # 집계자료 자체의 정합성 검증
    invalid_summary = (
        summary["income_type"].duplicated().any()
        or any(
            is_missing(value)
            for value in summary["income_type"]
        )
        or any(
            as_integer(value) is None or as_integer(value) < 0
            for col in SUMMARY_COLUMNS
            for value in summary[col]
        )
    )

    # 신고 상세자료 오류가 있으면 집계 대사를 보류
    if invalid_positions or invalid_summary:

        events.append(event(
            "SUMMARY", "ALL", "REC-04",
            "상세 또는 집계자료 정합성 오류로 집계 대사 보류",
            status="REVIEW"
        ))

        summary_results.append({
            "income_type": "ALL",
            "status": "BLOCKED",
            "message": "집계자료 정합성 확인 필요"
        })

    else:

        for col in DETAIL_AMOUNTS:
            details[col] = details[col].map(as_integer)

        summary = summary.copy()

        for col in SUMMARY_COLUMNS:
            summary[col] = summary[col].map(as_integer)

        expected_summary = make_summary(details)

        merged_summary = expected_summary.merge(
            summary,
            on="income_type",
            how="outer",
            suffixes=("_detail", "_filing"),
            indicator=True,
            validate="one_to_one"
        )

        for _, row in merged_summary.iterrows():

            key = row["income_type"]
            record = row.to_dict()

            different = []

            for col in SUMMARY_COLUMNS:

                expected = row[f"{col}_detail"]
                actual = row[f"{col}_filing"]

                if pd.isna(expected) or pd.isna(actual):
                    different.append(col)
                    record[f"{col}_diff"] = None
                else:
                    record[f"{col}_diff"] = actual - expected

                    if actual != expected:
                        different.append(col)

            record["status"] = "ERROR" if different else "PASS"

            record["message"] = (
                "집계 불일치: " + ", ".join(different)
                if different
                else "집계 일치"
            )

            summary_results.append(record)

            if different:

                events.append(event(
                    "SUMMARY",
                    key,
                    "REC-04",
                    record["message"]
                ))

    return (
        pd.DataFrame(detail_results),
        pd.DataFrame(summary_results),
        pd.DataFrame(events, columns=EVENT_COLUMNS)
    )
