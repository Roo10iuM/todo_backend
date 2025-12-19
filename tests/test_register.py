import pytest


@pytest.mark.asyncio
async def test_register_success(client):
    response = await client.post(
        "/api/register",
        json={"login": "user_1", "password": "Strong1!"},
    )

    assert response.status_code == 201
    assert response.json() == {"message": "user создан"}


@pytest.mark.asyncio
async def test_register_duplicate_login(client):
    await client.post(
        "/api/register",
        json={"login": "user_2", "password": "Strong1!"},
    )
    response = await client.post(
        "/api/register",
        json={"login": "user_2", "password": "Strong1!"},
    )

    assert response.status_code == 409
    assert response.json().get("detail") == "Login already exists"


@pytest.mark.asyncio
async def test_register_weak_password(client):
    response = await client.post(
        "/api/register",
        json={"login": "user_3", "password": "weak"},
    )

    assert response.status_code == 422
    detail = response.json().get("detail", [])
    assert any(item.get("loc", [])[-1] == "password" for item in detail)
