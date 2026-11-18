import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent))

import schemas


def test_public_payment_accepts_bkash_and_duration_only():
    payment = {
        "name": "Test Teacher",
        "email": "teacher@example.com",
        "phone": "01700000000",
        "plan": "Pro",
        "trx_id": "ABC123456",
        "method": "bkash",
        "subscription_duration": "six_month",
    }

    accepted = schemas.PublicPaymentCreate(**payment)
    assert accepted.method == "bkash"
    assert accepted.subscription_duration == "six_month"

    with pytest.raises(ValidationError):
        schemas.PublicPaymentCreate(**{**payment, "method": "nagad"})


def test_upgrade_accepts_canonical_bkash_and_offline_methods():
    assert schemas.PlanUpgradeCreate(
        requested_plan="Pro", method="bKash", trx_id="ABC123456",
        payment_phone="01700000000",
    ).method == "bKash"
    assert schemas.PlanUpgradeCreate(
        requested_plan="Pro", method="offline",
    ).method == "offline"
    assert schemas.PlanUpgradeCreate(
        requested_plan="Pro", method="other",
    ).method == "other"
    with pytest.raises(ValidationError):
        schemas.PlanUpgradeCreate(requested_plan="Pro", method="bkash")
    with pytest.raises(ValidationError):
        schemas.PlanUpgradeCreate(requested_plan="Pro", method="nagad")


def test_upgrade_validates_subscription_duration():
    assert schemas.PlanUpgradeCreate(
        requested_plan="Pro", subscription_duration="six_month",
    ).subscription_duration == "six_month"
    with pytest.raises(ValidationError):
        schemas.PlanUpgradeCreate(
            requested_plan="Pro", subscription_duration="yearly",
        )
