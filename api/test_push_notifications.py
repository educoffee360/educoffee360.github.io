import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))

import routes


class FakeQuery:
    def __init__(self, subscriptions):
        self.subscriptions = subscriptions
        self.user_ids = set()

    def filter(self, condition):
        self.user_ids = set(condition.right.value)
        return self

    def all(self):
        return [
            subscription for subscription in self.subscriptions
            if subscription.user_id in self.user_ids
        ]


class FakeDatabase:
    def __init__(self, subscriptions):
        self.subscriptions = subscriptions
        self.deleted = []
        self.commits = 0

    def query(self, model):
        assert model is routes.models.PushSubscription
        return FakeQuery(self.subscriptions)

    def delete(self, subscription):
        self.deleted.append(subscription)

    def commit(self):
        self.commits += 1


def test_push_delivery_targets_all_user_roles_and_removes_expired(monkeypatch):
    subscriptions = [
        SimpleNamespace(user_id="teacher-1", endpoint="expired"),
        SimpleNamespace(user_id="admin-1", endpoint="active"),
        SimpleNamespace(user_id="unrelated", endpoint="unrelated"),
    ]
    database = FakeDatabase(subscriptions)
    delivered = []

    def send(subscription, payload):
        delivered.append((subscription.endpoint, payload))
        return "expired" if subscription.endpoint == "expired" else True

    monkeypatch.setattr(routes, "_send_push", send)
    payload = {"title": "Update", "body": "Test"}

    routes._send_push_to_users(database, ["teacher-1", "admin-1"], payload)

    assert [endpoint for endpoint, _ in delivered] == ["expired", "active"]
    assert all(sent_payload is payload for _, sent_payload in delivered)
    assert database.deleted == [subscriptions[0]]
    assert database.commits == 1
