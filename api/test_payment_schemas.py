import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent))

import schemas


def test_public_payment_requires_bkash():
    payment = {
        "name": "Test Teacher",
        "email": "teacher@example.com",
        "phone": "01700000000",
        "plan": "Pro",
        "trx_id": "ABC123456",
    }

    accepted = schemas.PublicPaymentCreate(
        **payment, method="bkash", subscription_duration="six_month",
    )
    assert accepted.method == "bkash"
    assert accepted.subscription_duration == "six_month"
    with pytest.raises(ValidationError):
        schemas.PublicPaymentCreate(**payment, method="nagad")


def test_upgrade_accepts_bkash_and_offline_but_rejects_nagad():
    assert schemas.PlanUpgradeCreate(requested_plan="Pro").method == "bkash"
    assert schemas.PlanUpgradeCreate(
        requested_plan="Pro", method="bkash", trx_id="ABC123456",
        payment_phone="01700000000",
    ).method == "bkash"
    assert schemas.PlanUpgradeCreate(
        requested_plan="Pro", method="offline",
    ).method == "offline"
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