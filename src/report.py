from pathlib import Path

import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BASE_DIR / "outputs"

TAX_RULES = [
    [
        "INTEREST", "일반 과세 예금이자",
        "14%", "10%", "소액부징수 적용 제외",
        "소득세법 제86조, 제129조"
    ],
    [
        "BUSINESS", "계속적·반복적 인적용역",
        "3%", "10%", "소액부징수 적용 제외",
        "소득세법 제86조, 제129조; 시행령 제149조의3"
    ],
    [
        "OTHER", "일시적 강연료",
        "20%", "10%",
        "필요경비 60%, 소득금액 5만원 이하 과세최저한",
        "소득세법 제84조, 제129조; 시행령 제87조"
    ],
    [
        "LOCAL", "개인지방소득세",
        "-", "소득세의 10%", "특별징수",
        "지방세법 제103조의13"
    ],
    [
        "ROUNDING", "단수 처리",
        "-", "-", "지급 건별 10원 미만 절사 가정",
        "국고금 관리법 제47조; 지방회계법 제55조"
    ]
]


def evaluate_detection(events, truth):

    cols = ["scope", "key", "code"]

    expected = set(
        truth[cols].itertuples(index=False, name=None)
    )

    detected = set(
        events[cols].itertuples(index=False, name=None)
    )

    tp = len(expected & detected)
    fp = len(detected - expected)
    fn = len(expected - detected)

    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0

    return {
        "expected_findings": len(expected),
        "detected_findings": len(detected),
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "precision": precision,
        "recall": recall
    }


def create_report(
    transactions,
    events,
    detail_result,
    summary_result,
    truth
):

    OUTPUT_DIR.mkdir(exist_ok=True)

    output_path = OUTPUT_DIR / "validation_report.xlsx"

    metrics = evaluate_detection(events, truth)

    calculated = transactions.loc[
        transactions["tax_calculated"]
    ].copy()

    overview = pd.DataFrame([
        ("대상 지급월", "2026-10"),
        ("전체 지급자료 행 수", len(transactions)),
        ("원장 정상 행", int((transactions["status"] == "PASS").sum())),
        ("원장 오류 행", int((transactions["status"] == "ERROR").sum())),
        ("원장 추가 검토 행", int((transactions["status"] == "REVIEW").sum())),
        ("세액 비교 가능 행", len(calculated)),
        ("세액 비교 제외 행", len(transactions) - len(calculated)),
        ("거래별 대사 오류", int((detail_result["status"] == "ERROR").sum())),
        ("거래별 대사 보류", int((detail_result["status"] == "BLOCKED").sum())),
        ("집계 대사 오류", int((summary_result["status"] == "ERROR").sum())),
        ("소득세 과소징수", int(-calculated["income_tax_diff"].clip(upper=0).sum())),
        ("소득세 과다징수", int(calculated["income_tax_diff"].clip(lower=0).sum())),
        ("지방소득세 과소징수", int(-calculated["local_tax_diff"].clip(upper=0).sum())),
        ("지방소득세 과다징수", int(calculated["local_tax_diff"].clip(lower=0).sum())),
        ("검증 항목 탐지 수", metrics["detected_findings"]),
        ("오탐 수", metrics["false_positive"]),
        ("미탐 수", metrics["false_negative"]),
        ("Precision", f'{metrics["precision"]:.2%}'),
        ("Recall", f'{metrics["recall"]:.2%}'),
        ("범위", "가상 자료 및 지원 소득 유형에 한정"),
        ("주의", "실제 신고서가 아닌 신고 전 검증용 보고서")
    ], columns=["항목", "결과"])

    tax_summary = (
        calculated.groupby("income_type", as_index=False)
        .agg(
            payment_count=("payment_id", "size"),
            gross_amount=("gross_amount", "sum"),
            recorded_income_tax=("income_tax", "sum"),
            expected_income_tax=("expected_income_tax", "sum"),
            recorded_local_tax=("local_tax", "sum"),
            expected_local_tax=("expected_local_tax", "sum"),
            income_tax_diff=("income_tax_diff", "sum"),
            local_tax_diff=("local_tax_diff", "sum")
        )
    )

    tax_rules = pd.DataFrame(
        TAX_RULES,
        columns=[
            "구분", "적용 대상", "소득세율",
            "지방소득세율", "처리 기준", "법적 근거"
        ]
    )

    sheets = {
        "Summary": overview,
        "Tax Summary": tax_summary,
        "Transactions": transactions,
        "Errors": events[events["status"] == "ERROR"],
        "Review": events[events["status"] == "REVIEW"],
        "Reconciliation": detail_result,
        "Filing Summary": summary_result,
        "Tax Rules": tax_rules,
        "Ground Truth": truth
    }

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:

        for sheet_name, frame in sheets.items():

            frame.to_excel(
                writer,
                sheet_name=sheet_name,
                index=False
            )

            ws = writer.sheets[sheet_name]

            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions

            for cell in ws[1]:

                cell.font = Font(
                    bold=True,
                    color="FFFFFF"
                )

                cell.fill = PatternFill(
                    "solid",
                    fgColor="203864"
                )

                cell.alignment = Alignment(
                    horizontal="center"
                )

            for column in ws.columns:

                width = max(
                    len(str(cell.value or ""))
                    for cell in column
                )

                ws.column_dimensions[
                    get_column_letter(column[0].column)
                ].width = min(max(width + 4, 15), 65)

            for row in ws.iter_rows(min_row=2):

                for cell in row:

                    if cell.value == "ERROR":

                        cell.fill = PatternFill(
                            "solid", fgColor="FCE8E6"
                        )
                        cell.font = Font(color="B91C1C")

                    elif cell.value in ["REVIEW", "BLOCKED"]:

                        cell.fill = PatternFill(
                            "solid", fgColor="FFF2CC"
                        )

                    elif cell.value == "PASS":

                        cell.fill = PatternFill(
                            "solid", fgColor="E2F0D9"
                        )

                    if isinstance(cell.value, (int, float)):
                        cell.number_format = "#,##0"

    return output_path, metrics
