"""
Tests for task_manager.py.

Each test gets its own temporary tasks.json via the `task_file` fixture,
which patches the module-level TASKS_FILE so no real data is ever touched.
Functions are called directly for speed and clarity.
"""

import json
from datetime import date, timedelta

import pytest

import task_manager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def task_file(tmp_path, monkeypatch):
    """Redirect all I/O to an isolated temp file for every test."""
    tmp_tasks = tmp_path / "tasks.json"
    monkeypatch.setattr(task_manager, "TASKS_FILE", str(tmp_tasks))
    return tmp_tasks


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def stored_tasks(task_file):
    """Return the raw list currently written to disk."""
    if not task_file.exists():
        return []
    return json.loads(task_file.read_text())


# ---------------------------------------------------------------------------
# add_task
# ---------------------------------------------------------------------------


class TestAddTask:
    def test_add_minimal(self, task_file, capsys):
        """add with only a title defaults to medium priority and no due date."""
        task_manager.add_task("Buy milk")

        tasks = stored_tasks(task_file)
        assert len(tasks) == 1
        t = tasks[0]
        assert t["id"] == 1
        assert t["title"] == "Buy milk"
        assert t["priority"] == "medium"
        assert t["due"] is None
        assert t["done"] is False

        out = capsys.readouterr().out
        assert "Added task #1" in out
        assert "Buy milk" in out

    def test_add_with_priority(self, task_file):
        """add with an explicit priority stores that priority."""
        task_manager.add_task("Fix server", priority="high")

        t = stored_tasks(task_file)[0]
        assert t["priority"] == "high"

    def test_add_with_due_date(self, task_file):
        """add with a due date stores the date string."""
        task_manager.add_task("Submit report", due="2025-12-31")

        t = stored_tasks(task_file)[0]
        assert t["due"] == "2025-12-31"

    def test_add_with_all_fields(self, task_file):
        """add with every optional argument stores all fields correctly."""
        task_manager.add_task("Deploy release", priority="high", due="2025-06-01")

        t = stored_tasks(task_file)[0]
        assert t["title"] == "Deploy release"
        assert t["priority"] == "high"
        assert t["due"] == "2025-06-01"

    def test_add_multiple_tasks_increments_id(self, task_file):
        """Each new task receives a unique, incrementing ID."""
        task_manager.add_task("First")
        task_manager.add_task("Second")
        task_manager.add_task("Third")

        tasks = stored_tasks(task_file)
        assert [t["id"] for t in tasks] == [1, 2, 3]


# ---------------------------------------------------------------------------
# list_tasks
# ---------------------------------------------------------------------------


class TestListTasks:
    @pytest.fixture(autouse=True)
    def _seed(self, task_file):
        """Pre-populate the file with a known set of tasks."""
        task_manager.add_task("Pending low", priority="low")
        task_manager.add_task("Pending high", priority="high")
        task_manager.add_task("Done medium", priority="medium")
        # mark task #3 as done
        task_manager.complete_task(3)

    def test_list_all(self, capsys):
        """list with no filter shows every task."""
        task_manager.list_tasks()
        out = capsys.readouterr().out
        assert "Pending low" in out
        assert "Pending high" in out
        assert "Done medium" in out

    def test_list_pending(self, capsys):
        """list 'pending' shows only tasks not yet done."""
        task_manager.list_tasks(filter_status="pending")
        out = capsys.readouterr().out
        assert "Pending low" in out
        assert "Pending high" in out
        assert "Done medium" not in out

    def test_list_done(self, capsys):
        """list 'done' shows only completed tasks."""
        task_manager.list_tasks(filter_status="done")
        out = capsys.readouterr().out
        assert "Done medium" in out
        assert "Pending low" not in out
        assert "Pending high" not in out

    def test_list_by_priority(self, capsys):
        """list filtered by priority shows only matching tasks."""
        task_manager.list_tasks(priority="high")
        out = capsys.readouterr().out
        assert "Pending high" in out
        assert "Pending low" not in out
        assert "Done medium" not in out

    def test_list_done_with_priority_filter(self, capsys):
        """Combined done + priority filter narrows results correctly."""
        task_manager.list_tasks(filter_status="done", priority="medium")
        out = capsys.readouterr().out
        assert "Done medium" in out
        assert "Pending high" not in out

    def test_list_empty_prints_no_tasks(self, task_file, capsys):
        """list on an empty store prints a 'no tasks' message."""
        task_file.write_text("[]")
        task_manager.list_tasks()
        out = capsys.readouterr().out
        assert "No tasks found." in out

    def test_list_output_shows_status_and_priority(self, capsys):
        """Each output line contains the status label and priority label."""
        task_manager.list_tasks(filter_status="pending", priority="low")
        out = capsys.readouterr().out
        assert "pending" in out
        assert "LOW" in out

    def test_list_shows_due_date_when_present(self, task_file, capsys):
        """Due date appears in list output when set."""
        task_manager.add_task("Review PR", due="2025-07-04")
        task_manager.list_tasks()
        out = capsys.readouterr().out
        assert "2025-07-04" in out


# ---------------------------------------------------------------------------
# complete_task
# ---------------------------------------------------------------------------


class TestCompleteTask:
    def test_complete_marks_done(self, task_file, capsys):
        """complete sets done=True on the correct task."""
        task_manager.add_task("Write docs")
        task_manager.complete_task(1)

        t = stored_tasks(task_file)[0]
        assert t["done"] is True

        out = capsys.readouterr().out
        assert "marked as done" in out

    def test_complete_only_affects_target_task(self, task_file):
        """Completing one task leaves other tasks untouched."""
        task_manager.add_task("Task A")
        task_manager.add_task("Task B")
        task_manager.complete_task(1)

        tasks = stored_tasks(task_file)
        assert tasks[0]["done"] is True
        assert tasks[1]["done"] is False

    def test_complete_nonexistent_id(self, task_file, capsys):
        """Completing a missing ID prints a not-found message without crashing."""
        task_manager.add_task("Only task")
        task_manager.complete_task(999)

        out = capsys.readouterr().out
        assert "not found" in out

        # The existing task must remain unchanged
        assert stored_tasks(task_file)[0]["done"] is False


# ---------------------------------------------------------------------------
# delete_task
# ---------------------------------------------------------------------------


class TestDeleteTask:
    def test_delete_removes_task(self, task_file, capsys):
        """delete removes the task from storage."""
        task_manager.add_task("Temporary task")
        task_manager.delete_task(1)

        assert stored_tasks(task_file) == []

        out = capsys.readouterr().out
        assert "Deleted task #1" in out

    def test_delete_only_removes_target(self, task_file):
        """Deleting one task leaves the others intact."""
        task_manager.add_task("Keep me")
        task_manager.add_task("Delete me")
        task_manager.delete_task(2)

        tasks = stored_tasks(task_file)
        assert len(tasks) == 1
        assert tasks[0]["title"] == "Keep me"

    def test_delete_nonexistent_id_is_silent(self, task_file):
        """Deleting a non-existent ID does not crash or corrupt data."""
        task_manager.add_task("Real task")
        task_manager.delete_task(999)

        # Original task must still be present
        assert len(stored_tasks(task_file)) == 1


# ---------------------------------------------------------------------------
# show_overdue
# ---------------------------------------------------------------------------


class TestShowOverdue:
    def _past(self, days=1):
        return (date.today() - timedelta(days=days)).isoformat()

    def _future(self, days=1):
        return (date.today() + timedelta(days=days)).isoformat()

    def test_overdue_task_appears(self, task_file, capsys):
        """A pending task with a past due date is listed."""
        task_manager.add_task("Overdue chore", due=self._past(2))
        task_manager.show_overdue()

        out = capsys.readouterr().out
        assert "Overdue chore" in out

    def test_future_task_not_overdue(self, task_file, capsys):
        """A pending task with a future due date is not listed."""
        task_manager.add_task("Future task", due=self._future(5))
        task_manager.show_overdue()

        out = capsys.readouterr().out
        assert "No overdue tasks." in out

    def test_completed_past_due_not_overdue(self, task_file, capsys):
        """A done task is never reported as overdue even if past due."""
        task_manager.add_task("Already done", due=self._past(3))
        task_manager.complete_task(1)
        task_manager.show_overdue()

        out = capsys.readouterr().out
        assert "No overdue tasks." in out

    def test_no_due_date_not_overdue(self, task_file, capsys):
        """A task with no due date is never reported as overdue."""
        task_manager.add_task("No deadline")
        task_manager.show_overdue()

        out = capsys.readouterr().out
        assert "No overdue tasks." in out

    def test_empty_store_not_overdue(self, capsys):
        """An empty task list reports no overdue tasks."""
        task_manager.show_overdue()

        out = capsys.readouterr().out
        assert "No overdue tasks." in out

    def test_overdue_shows_due_date(self, task_file, capsys):
        """The overdue listing includes the original due date."""
        due = self._past(4)
        task_manager.add_task("Past deadline", due=due)
        task_manager.show_overdue()

        out = capsys.readouterr().out
        assert due in out

    def test_only_overdue_tasks_listed(self, task_file, capsys):
        """When mixed, only past-due pending tasks appear."""
        task_manager.add_task("Overdue one", due=self._past(1))
        task_manager.add_task("Fine task", due=self._future(1))
        task_manager.add_task("No due task")
        capsys.readouterr()  # discard add_task output before asserting on overdue
        task_manager.show_overdue()

        out = capsys.readouterr().out
        assert "Overdue one" in out
        assert "Fine task" not in out
        assert "No due task" not in out
