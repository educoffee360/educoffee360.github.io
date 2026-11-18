import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parent))

import schemas


def test_public_payment_accepts_bkash_and_rejects_nagad():
    payment = {
        "name": "Test Teacher",
        "email": "teacher@example.com",
        "phone": "01700000000",
        "plan": "Pro",
        "trx_id": "ABC123456",
    }

    accepted = schemas.PublicPaymentCreate(
        **payment, method="bkash", subscription_duration="six_month"
    )
    assert accepted.method == "bkash"
    assert accepted.subscription_duration == "six_month"
    with pytest.raises(ValidationError):
        schemas.PublicPaymentCreate(**payment, method="nagad")


def test_upgrade_defaults_to_bkash_and_validates_duration():
    request = schemas.PlanUpgradeCreate(
        requested_plan="Pro",
        trx_id="ABC123456",
        payment_phone="01700000000",
        subscription_duration="six_month",
    )

    assert request.method == "bkash"
    assert request.subscription_duration == "six_month"

    with pytest.raises(ValidationError):
        schemas.PlanUpgradeCreate(requested_plan="Pro", method="nagad")
