
import os
from unittest.mock import patch

# Provide a temporary database URL for CI
with patch.dict(os.environ, {"DATABASE_URL": "sqlite://"}):
    with patch("sqlalchemy.schema.MetaData.create_all"):
        import main

from fastapi.testclient import TestClient
from sqlalchemy import Column, Integer, String, Boolean

from test_database import (
    TestBase,
    test_engine,
    TestingSessionLocal,
)

# Define the Task table in the temporary test database
class TestTask(TestBase):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    completed = Column(Boolean, default=False)


# Create tables in the temporary SQLite database
TestBase.metadata.create_all(bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


main.app.dependency_overrides[main.get_db] = override_get_db

client = TestClient(main.app)


def setup_function():
    TestBase.metadata.drop_all(bind=test_engine)
    TestBase.metadata.create_all(bind=test_engine)


def test_home():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Task Manager API is running"
    }


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy"
    }


def test_create_task():
    response = client.post(
        "/tasks",
        json={"title": "Learn automated testing"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Learn automated testing"
    assert response.json()["completed"] is False
    assert "id" in response.json()


def test_get_tasks():
    client.post("/tasks", json={"title": "First task"})
    client.post("/tasks", json={"title": "Second task"})

    response = client.get("/tasks")

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["title"] == "First task"
    assert response.json()[1]["title"] == "Second task"


def test_get_single_task():
    create_response = client.post(
        "/tasks",
        json={"title": "My task"},
    )
    task_id = create_response.json()["id"]

    response = client.get(f"/tasks/{task_id}")

    assert response.status_code == 200
    assert response.json()["title"] == "My task"


def test_update_task():
    create_response = client.post(
        "/tasks",
        json={"title": "Old title"},
    )
    task_id = create_response.json()["id"]

    response = client.put(
        f"/tasks/{task_id}",
        json={"title": "Updated title"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated title"


def test_delete_task():
    create_response = client.post(
        "/tasks",
        json={"title": "Task to delete"},
    )
    task_id = create_response.json()["id"]

    response = client.delete(f"/tasks/{task_id}")

    assert response.status_code == 200
    assert response.json()["message"] == "Task deleted successfully"

    get_response = client.get(f"/tasks/{task_id}")
    assert get_response.status_code == 404


def test_task_not_found():
    response = client.get("/tasks/99999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"
