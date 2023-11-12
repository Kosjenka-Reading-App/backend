from conftest import client
from utils import auth_header


def test_create_account(superadmin_token):
    accounts = client.get(
        "http://localhost:8000/accounts", headers=auth_header(superadmin_token)
    ).json()
    account_count = len(accounts)
    new_account = {
        "email": "email@gmail.com",
        "password": "secret",
    }
    resp = client.post(
        "http://localhost:8000/accounts",
        json=new_account,
        headers=auth_header(superadmin_token),
    )
    assert resp.status_code == 200
    accounts = client.get(
        "http://localhost:8000/accounts", headers=auth_header(superadmin_token)
    ).json()
    assert len(accounts) == account_count + 1


def test_update_account(superadmin_token):
    accounts = client.get(
        "http://localhost:8000/accounts", headers=auth_header(superadmin_token)
    ).json()
    account_id = accounts[0]["id_account"]
    original_account = client.get(
        f"http://localhost:8000/accounts/{account_id}",
        headers=auth_header(superadmin_token),
    ).json()
    body = {"email": "update@gmail.com"}
    client.patch(
        f"http://localhost:8000/accounts/{account_id}",
        json=body,
        headers=auth_header(superadmin_token),
    ).json()
    updated_account = client.get(
        f"http://localhost:8000/accounts/{account_id}",
        headers=auth_header(superadmin_token),
    ).json()
    for key in updated_account:
        if key == "email":
            assert updated_account[key] == "update@gmail.com"
            continue
        assert updated_account[key] == original_account[key]


def test_search_account(superadmin_token):
    new_account = {
        "email": "exercise_master@gmail.com",
        "password": "secret",
    }
    resp = client.post(
        "http://localhost:8000/accounts",
        json=new_account,
        headers=auth_header(superadmin_token),
    )
    assert resp.status_code == 200
    accounts = client.get(
        "http://localhost:8000/accounts?email_like=email@",
        headers=auth_header(superadmin_token),
    ).json()
    assert len(accounts) == 1
    assert accounts[0]["email"] == "email@gmail.com"


def test_sort_account(superadmin_token):
    accounts = client.get(
        "http://localhost:8000/accounts", headers=auth_header(superadmin_token)
    ).json()
    assert len(accounts) >= 2
    sorted_emails = sorted([acc["email"] for acc in accounts])
    assert sorted_emails == [
        acc["email"]
        for acc in client.get(
            "http://localhost:8000/accounts?order_by=email",
            headers=auth_header(superadmin_token),
        ).json()
    ]
    assert sorted_emails[::-1] == [
        acc["email"]
        for acc in client.get(
            "http://localhost:8000/accounts?order_by=email&order=desc",
            headers=auth_header(superadmin_token),
        ).json()
    ]


def test_delete_account(superadmin_token):
    accounts = client.get(
        "http://localhost:8000/accounts", headers=auth_header(superadmin_token)
    ).json()
    assert len(accounts) > 0
    account_ids = {
        ex["id_account"] for ex in accounts if ex["account_category"] == "admin"
    }
    while account_ids:
        account_id = account_ids.pop()
        client.delete(
            f"http://localhost:8000/accounts/{account_id}",
            headers=auth_header(superadmin_token),
        ).json()
        remaining_account_ids = {
            ex["id_account"]
            for ex in client.get(
                "http://localhost:8000/accounts", headers=auth_header(superadmin_token)
            ).json()
            if ex["account_category"] == "admin"
        }
        assert len(remaining_account_ids) == len(account_ids)
        assert account_id not in remaining_account_ids


def test_me_endpoint(regular_token):
    resp = client.get(
        "http://localhost:8000/me", headers=auth_header(regular_token)
    ).json()
    print(resp)
    assert resp["account_category"] == "regular"
