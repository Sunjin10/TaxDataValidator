from pathlib import Path
from time import perf_counter
import argparse

import pandas as pd

from src.generate_data import generate_data
from src.validator import validate_payments
from src.reconciliation import reconcile
from src.report import create_report

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


def main(regenerate=True):

    start = perf_counter()

    if regenerate:
        generate_data(seed=42)

    payments = pd.read_csv(
        DATA_DIR / "payments.csv",
        keep_default_na=False
    )

    details = pd.read_csv(
        DATA_DIR / "filing_details.csv",
        keep_default_na=False
    )

    summary = pd.read_csv(
        DATA_DIR / "filing_summary.csv",
        keep_default_na=False
    )

    truth = pd.read_csv(
        DATA_DIR / "ground_truth.csv",
        keep_default_na=False
    )

    transactions, payment_events = validate_payments(payments)

    detail_result, summary_result, rec_events = reconcile(
        transactions,
        details,
        summary
    )

    events = pd.concat(
        [payment_events, rec_events],
        ignore_index=True
    )

    report_path, metrics = create_report(
        transactions,
        events,
        detail_result,
        summary_result,
        truth
    )

    elapsed = perf_counter() - start

    print("=" * 50)
    print("TaxDataValidator 1.0")
    print("=" * 50)

    print(f"지급자료: {len(payments)}건")
    print(f"정상 행: {(transactions['status'] == 'PASS').sum()}건")
    print(f"오류 행: {(transactions['status'] == 'ERROR').sum()}건")
    print(f"검토 행: {(transactions['status'] == 'REVIEW').sum()}건")

    print("-" * 50)

    print(f"탐지 항목: {metrics['detected_findings']}건")
    print(f"오탐: {metrics['false_positive']}건")
    print(f"미탐: {metrics['false_negative']}건")
    print(f"Precision: {metrics['precision']:.2%}")
    print(f"Recall: {metrics['recall']:.2%}")

    print("-" * 50)

    print(f"실행시간: {elapsed:.4f}초")
    print(f"보고서: {report_path}")

    return elapsed, metrics


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--reuse-data",
        action="store_true"
    )

    args = parser.parse_args()

    main(regenerate=not args.reuse_data)
