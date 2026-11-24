import pytest

from src.tax_rules import (
    calculate_tax,
    truncate_10,
    ReviewRequired,
    SUBTYPES
)


@pytest.mark.parametrize(
    "kind,gross,expected_tax,expected_local",
    [
        ("INTEREST", 1000000, 140000, 14000),
        ("INTEREST", 5000, 700, 70),
        ("INTEREST", 10000, 1400, 140),
        ("INTEREST", 200000, 28000, 2800),
        ("BUSINESS", 1000000, 30000, 3000),
        ("BUSINESS", 30000, 900, 90),
        ("BUSINESS", 20000, 600, 60),
        ("BUSINESS", 800000, 24000, 2400),
        ("OTHER", 1000000, 80000, 8000),
        ("OTHER", 500000, 40000, 4000),
        ("OTHER", 120000, 0, 0),
        ("OTHER", 124995, 0, 0),
        ("OTHER", 125000, 0, 0),
        ("OTHER", 125005, 10000, 1000),
        ("OTHER", 125100, 10000, 1000),
        ("OTHER", 125125, 10010, 1000),
        ("BUSINESS", 33300, 990, 90),
        ("BUSINESS", 33400, 1000, 100),
        ("INTEREST", 7142, 990, 90),
        ("INTEREST", 7143, 1000, 100)
    ]
)
def test_calculate_tax(
    kind, gross, expected_tax, expected_local
):

    result = calculate_tax(
        kind,
        gross,
        income_subtype=SUBTYPES[kind]
    )

    assert result["income_tax"] == expected_tax
    assert result["local_tax"] == expected_local

    assert result["net_amount"] == (
        gross - expected_tax - expected_local
    )


@pytest.mark.parametrize(
    "amount,expected",
    [
        (1234, 1230),
        (1238, 1230),
        (999, 990),
        (9, 0),
        (1000, 1000)
    ]
)
def test_truncate_10(amount, expected):

    assert truncate_10(amount) == expected


@pytest.mark.parametrize(
    "gross",
    [-100000, 0, None, "100000", 100000.5, True]
)
def test_invalid_amount(gross):

    with pytest.raises(ValueError):
        calculate_tax(
            "BUSINESS",
            gross,
            income_subtype="RECURRING_SERVICE"
        )


def test_non_resident():

    with pytest.raises(ReviewRequired):
        calculate_tax(
            "INTEREST",
            1000000,
            "NON_RESIDENT",
            "BANK_DEPOSIT"
        )


def test_unsupported_income():

    with pytest.raises(ReviewRequired):
        calculate_tax("SALARY", 3000000)


def test_unsupported_subtype():

    with pytest.raises(ReviewRequired):
        calculate_tax(
            "INTEREST",
            1000000,
            income_subtype="TAX_EXEMPT"
        )


def test_missing_subtype():

    with pytest.raises(ReviewRequired):
        calculate_tax("OTHER", 1000000)


def test_fractional_expense_review():

    with pytest.raises(ReviewRequired):
        calculate_tax(
            "OTHER",
            125001,
            income_subtype="ONE_TIME_LECTURE"
        )


def test_expense_amount():

    result = calculate_tax(
        "OTHER",
        500000,
        income_subtype="ONE_TIME_LECTURE"
    )

    assert result["expense_amount"] == 300000
    assert result["tax_base"] == 200000
