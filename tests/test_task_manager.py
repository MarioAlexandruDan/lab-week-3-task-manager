"""
Tests for task_manager.py.

Each test patches task_manager.TASKS_FILE to a fresh temporary file so no
test touches real data and tests never interfere with each other.
"""

import json
import os
from datetime import date, timedelta

import pytest

import task_manager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def isolated_tasks_file(tmp_path, monkeypatch):
    """Redirect every load/save call to a per-test temp file."""
    tmp_file = str(tmp_path / "tasks.json")
    monkeypatch.setattr(task_manager, "TASKS_FILE", tmp_file)
    yield tmp_file


def read_tasks(path):
    """Load the raw task list from the temp file."""
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# add_task
# ---------------------------------------------------------------------------

class TestAddTask:
    def test_add_minimal(self, isolated_tasks_file, capsys):
        """add with title only → default priority=medium, no due date."""
        task_manager.add_task("Buy milk")

        tasks = read_tasks(isolated_tasks_file)
        assert len(tasks) == 1
        t = tasks[0]
        assert t["title"] == "Buy milk"
        assert t["priority"] == "medium"
        assert t["due"] is None
        assert t["done"] is False
        assert t["id"] == 1

        out = capsys.readouterr().out
        assert "Added task #1" in out
        assert "Buy milk" in out

    def test_add_with_priority(self, isolated_tasks_file):
        """add with explicit priority stores it correctly."""
        task_manager.add_task("Fix bug", priority="high")

        tasks = read_tasks(isolated_tasks_file)
        assert tasks[0]["priority"] == "high"

    def test_add_with_due_date(self, isolated_tasks_file):
        """add with a due date stores it correctly."""
        task_manager.add_task("Submit report", due="2025-12-31")

        tasks = read_tasks(isolated_tasks_file)
        assert tasks[0]["due"] == "2025-12-31"

    def test_add_with_priority_and_due(self, isolated_tasks_file):
        """add with both priority and due date."""
        task_manager.add_task("Deploy release", priority="low", due="2025-06-01")

        tasks = read_tasks(isolated_tasks_file)
        t = tasks[0]
        assert t["priority"] == "low"
        assert t["due"] == "2025-06-01"

    def test_add_multiple_tasks_get_sequential_ids(self, isolated_tasks_file):
        """Each new task receives the next available integer id."""
        task_manager.add_task("Task A")
        task_manager.add_task("Task B")
        task_manager.add_task("Task C")

        tasks = read_tasks(isolated_tasks_file)
        assert [t["id"] for t in tasks] == [1, 2, 3]


# ---------------------------------------------------------------------------
# list_tasks
# ---------------------------------------------------------------------------

class TestListTasks:
    @pytest.fixture(autouse=True)
    def seed_tasks(self, isolated_tasks_file):
        """Pre-populate three tasks: two pending (high/low) + one done (medium)."""
        task_manager.add_task("High pending", priority="high")
        task_manager.add_task("Low pending", priority="low")
        task_manager.add_task("Done medium", priority="medium")
        task_manager.complete_task(3)  # mark the third task done

    def test_list_all(self, capsys):
        """list with no filter prints all tasks."""
        task_manager.list_tasks()
        out = capsys.readouterr().out
        assert "High pending" in out
        assert "Low pending" in out
        assert "Done medium" in out

    def test_list_pending(self, capsys):
        """list pending shows only incomplete tasks."""
        task_manager.list_tasks(filter_status="pending")
        out = capsys.readouterr().out
        assert "High pending" in out
        assert "Low pending" in out
        assert "Done medium" not in out

    def test_list_done(self, capsys):
        """list done shows only completed tasks."""
        task_manager.list_tasks(filter_status="done")
        out = capsys.readouterr().out
        assert "Done medium" in out
        assert "High pending" not in out
        assert "Low pending" not in out

    def test_list_by_priority(self, capsys):
        """list with priority filter shows only matching-priority tasks."""
        task_manager.list_tasks(priority="high")
        out = capsys.readouterr().out
        assert "High pending" in out
        assert "Low pending" not in out
        assert "Done medium" not in out

    def test_list_done_status_label(self, capsys):
        """Completed tasks are labelled [done]; pending tasks are [pending]."""
        task_manager.list_tasks()
        out = capsys.readouterr().out
        lines = out.splitlines()
        done_lines = [l for l in lines if "Done medium" in l]
        pending_lines = [l for l in lines if "High pending" in l]
        assert done_lines and "[done]" in done_lines[0]
        assert pending_lines and "[pending]" in pending_lines[0]

    def test_list_shows_due_date(self, capsys):
        """Due date is shown in output when set."""
        task_manager.add_task("Has due date", due="2025-09-01")
        task_manager.list_tasks()
        out = capsys.readouterr().out
        assert "due: 2025-09-01" in out

    def test_list_empty(self, isolated_tasks_file, capsys):
        """list on an empty store prints 'No tasks found.'."""
        # Override the seeded store with an empty one
        with open(isolated_tasks_file, "w") as f:
            json.dump([], f)

        task_manager.list_tasks()
        out = capsys.readouterr().out
        assert "No tasks found." in out


# ---------------------------------------------------------------------------
# complete_task
# ---------------------------------------------------------------------------

class TestCompleteTask:
    def test_complete_marks_done(self, isolated_tasks_file, capsys):
        """complete_task flips done to True and persists it."""
        task_manager.add_task("Write tests")
        task_manager.complete_task(1)

        tasks = read_tasks(isolated_tasks_file)
        assert tasks[0]["done"] is True

        out = capsys.readouterr().out
        assert "marked as done" in out

    def test_complete_only_affects_target(self, isolated_tasks_file):
        """Completing one task does not alter other tasks."""
        task_manager.add_task("Task A")
        task_manager.add_task("Task B")
        task_manager.complete_task(1)

        tasks = read_tasks(isolated_tasks_file)
        assert tasks[0]["done"] is True   # task 1 → done
        assert tasks[1]["done"] is False  # task 2 → unchanged

    def test_complete_nonexistent_task(self, capsys):
        """complete_task on a missing id prints a 'not found' message."""
        task_manager.complete_task(99)
        out = capsys.readouterr().out
        assert "not found" in out


# ---------------------------------------------------------------------------
# delete_task
# ---------------------------------------------------------------------------

class TestDeleteTask:
    def test_delete_removes_task(self, isolated_tasks_file, capsys):
        """delete_task removes the task from the store."""
        task_manager.add_task("Temporary task")
        task_manager.delete_task(1)

        tasks = read_tasks(isolated_tasks_file)
        assert tasks == []

        out = capsys.readouterr().out
        assert "Deleted task #1" in out

    def test_delete_leaves_other_tasks(self, isolated_tasks_file):
        """Deleting one task does not remove other tasks."""
        task_manager.add_task("Keep me")
        task_manager.add_task("Delete me")
        task_manager.delete_task(2)

        tasks = read_tasks(isolated_tasks_file)
        assert len(tasks) == 1
        assert tasks[0]["title"] == "Keep me"

    def test_delete_nonexistent_task_is_silent(self, isolated_tasks_file):
        """Deleting a non-existent id leaves the store unchanged."""
        task_manager.add_task("Only task")
        task_manager.delete_task(99)

        tasks = read_tasks(isolated_tasks_file)
        assert len(tasks) == 1


# ---------------------------------------------------------------------------
# show_overdue
# ---------------------------------------------------------------------------

class TestShowOverdue:
    def _yesterday(self):
        return (date.today() - timedelta(days=1)).isoformat()

    def _tomorrow(self):
        return (date.today() + timedelta(days=1)).isoformat()

    def test_overdue_past_due_pending(self, capsys):
        """A pending task with a past due date appears in overdue output."""
        task_manager.add_task("Late task", due=self._yesterday())
        task_manager.show_overdue()

        out = capsys.readouterr().out
        assert "Late task" in out

    def test_overdue_future_due_not_listed(self, capsys):
        """A pending task due in the future is NOT overdue."""
        task_manager.add_task("Future task", due=self._tomorrow())
        capsys.readouterr()  # discard setup output
        task_manager.show_overdue()

        out = capsys.readouterr().out
        assert "Future task" not in out
        assert "No overdue tasks." in out

    def test_overdue_done_task_excluded(self, capsys):
        """A completed task is never overdue, even with a past due date."""
        task_manager.add_task("Done late", due=self._yesterday())
        task_manager.complete_task(1)
        capsys.readouterr()  # discard setup output
        task_manager.show_overdue()

        out = capsys.readouterr().out
        assert "Done late" not in out
        assert "No overdue tasks." in out

    def test_overdue_no_due_date_excluded(self, capsys):
        """Tasks without a due date never appear as overdue."""
        task_manager.add_task("No due date")
        capsys.readouterr()  # discard setup output
        task_manager.show_overdue()

        out = capsys.readouterr().out
        assert "No due date" not in out
        assert "No overdue tasks." in out

    def test_overdue_empty_store(self, capsys):
        """show_overdue on an empty store prints 'No overdue tasks.'"""
        task_manager.show_overdue()
        out = capsys.readouterr().out
        assert "No overdue tasks." in out

    def test_overdue_mixed_tasks(self, capsys):
        """Only the past-due pending task surfaces among a mixed set."""
        task_manager.add_task("Overdue one", due=self._yesterday())
        task_manager.add_task("Future one", due=self._tomorrow())
        task_manager.add_task("Done overdue", due=self._yesterday())
        task_manager.complete_task(3)
        capsys.readouterr()  # discard setup output
        task_manager.show_overdue()

        out = capsys.readouterr().out
        assert "Overdue one" in out
        assert "Future one" not in out
        assert "Done overdue" not in out
