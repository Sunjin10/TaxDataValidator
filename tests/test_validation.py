import pandas as pd
import pytest

from src.generate_data import generate_data
from src.validator import validate_payments
from src.reconciliation import reconcile
from src.report import evaluate_detection


@pytest.fixture(scope="module")
def sample():

    payments, details, summary, truth = generate_data()

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

    return {
        "payments": payments,
        "details": details,
        "summary": summary,
        "truth": truth,
        "transactions": transactions,
        "events": events,
        "detail_result": detail_result,
        "summary_result": summary_result
    }


@pytest.mark.parametrize(
    "row_id,code",
    [
        ("R001", "DATA-01"),
        ("R002", "DATA-03"),
        ("R003", "DATA-04"),
        ("R004", "TAX-01"),
        ("R005", "TAX-02"),
        ("R006", "TAX-03"),
        ("R007", "TAX-04"),
        ("R008", "TAX-05"),
        ("R009", "TAX-06"),
        ("R010", "DATA-02"),
        ("R200", "DATA-02")
    ]
)
def test_payment_errors(sample, row_id, code):

    events = sample["events"]

    assert (
        (events["scope"] == "PAYMENT")
        & (events["key"] == row_id)
        & (events["code"] == code)
    ).any()


@pytest.mark.parametrize(
    "key,code",
    [
        ("P011", "REC-01"),
        ("P012", "REC-03"),
        ("P999", "REC-02"),
        ("INTEREST", "REC-04"),
        ("BUSINESS", "REC-04"),
        ("OTHER", "REC-04")
    ]
)
def test_reconciliation(sample, key, code):

    events = sample["events"]

    assert (
        (events["key"] == key)
        & (events["code"] == code)
    ).any()


def test_dataset_size(sample):

    assert len(sample["payments"]) == 200


def test_normal_transactions(sample):

    assert (
        sample["transactions"]["status"] == "PASS"
    ).sum() == 189


def test_review_status(sample):

    row = sample["transactions"].loc[
        sample["transactions"]["row_id"] == "R004"
    ].iloc[0]

    assert row["status"] == "REVIEW"
    assert not row["tax_calculated"]


def test_duplicate_exclusion(sample):

    rows = sample["transactions"].loc[
        sample["transactions"]["payment_id"] == "P010"
    ]

    assert len(rows) == 2
    assert not rows["reconciliation_eligible"].any()


def test_missing_column(sample):

    frame = sample["payments"].drop(
        columns=["gross_amount"]
    )

    with pytest.raises(ValueError):
        validate_payments(frame)


def test_invalid_date(sample):

    frame = sample["payments"].iloc[[15]].copy()
    frame.loc[:, "payment_date"] = "2026-11-01"

    _, events = validate_payments(frame)

    assert "DATA-04" in events["code"].values


def test_expense_review(sample):

    frame = sample["payments"].iloc[[6]].copy()

    frame.loc[:, "expense_amount"] = 90000
    frame.loc[:, "income_tax"] = 0
    frame.loc[:, "net_amount"] = 125000

    transactions, events = validate_payments(frame)

    assert transactions.iloc[0]["status"] == "REVIEW"
    assert "TAX-07" in events["code"].values


def test_duplicate_filing(sample):

    details = pd.concat(
        [
            sample["details"],
            sample["details"].iloc[[20]]
        ],
        ignore_index=True
    )

    _, summary_result, events = reconcile(
        sample["transactions"],
        details,
        sample["summary"]
    )

    assert "DATA-02" in events["code"].values
    assert "BLOCKED" in summary_result["status"].values


def test_filing_invalid_amount(sample):

    details = sample["details"].copy()
    details.loc[20, "gross_amount"] = -50000

    _, _, events = reconcile(
        sample["transactions"],
        details,
        sample["summary"]
    )

    assert "DATA-03" in events["code"].values


def test_detection_precision(sample):

    metrics = evaluate_detection(
        sample["events"],
        sample["truth"]
    )

    assert metrics["precision"] == 1.0


def test_detection_recall(sample):

    metrics = evaluate_detection(
        sample["events"],
        sample["truth"]
    )

    assert metrics["recall"] == 1.0


def test_reproducibility(sample):

    payments, details, summary, truth = generate_data(seed=42)

    pd.testing.assert_frame_equal(
        sample["payments"],
        payments
    )

    pd.testing.assert_frame_equal(
        sample["details"],
        details
    )

    pd.testing.assert_frame_equal(
        sample["summary"],
        summary
    )
