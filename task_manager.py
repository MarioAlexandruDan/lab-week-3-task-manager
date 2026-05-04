import json
import os
import sys
from datetime import datetime

TASKS_FILE = "tasks.json"


def load_tasks():
    if not os.path.exists(TASKS_FILE):
        return []
    with open(TASKS_FILE, "r") as f:
        return json.load(f)


def save_tasks(tasks):
    with open(TASKS_FILE, "w") as f:
        json.dump(tasks, f, indent=2)


def next_id(tasks):
    return max((t["id"] for t in tasks), default=0) + 1


def add_task(title, priority="medium", due=None):
    tasks = load_tasks()
    task = {
        "id": next_id(tasks),
        "title": title,
        "priority": priority,
        "due": due,
        "done": False,
        "created": datetime.now().isoformat(),
    }
    tasks.append(task)
    save_tasks(tasks)
    print(f"Added task #{task['id']}: {title}")


def complete_task(*task_ids):
    tasks = load_tasks()
    id_to_task = {t["id"]: t for t in tasks}
    for task_id in task_ids:
        if task_id in id_to_task:
            id_to_task[task_id]["done"] = True
            print(f"Task #{task_id} marked as done.")
        else:
            print(f"Task #{task_id} not found.")
    save_tasks(tasks)


def delete_task(task_id):
    tasks = load_tasks()
    tasks = [t for t in tasks if t["id"] != task_id]
    save_tasks(tasks)
    print(f"Deleted task #{task_id}.")


def list_tasks(filter_status=None, priority=None):
    tasks = load_tasks()

    if filter_status == "done":
        tasks = [t for t in tasks if t["done"]]
    elif filter_status == "pending":
        tasks = [t for t in tasks if not t["done"]]

    if priority:
        tasks = [t for t in tasks if t["priority"] == priority]

    if not tasks:
        print("No tasks found.")
        return

    for t in tasks:
        status = "done" if t["done"] else "pending"
        due_str = f" (due: {t['due']})" if t["due"] else ""
        print(f"[{status}] #{t['id']} [{t['priority'].upper()}] {t['title']}{due_str}")


def show_overdue():
    tasks = load_tasks()
    today = datetime.now().date()
    overdue = [
        t
        for t in tasks
        if t["due"] and not t["done"] and datetime.fromisoformat(t["due"]).date() < today
    ]
    if not overdue:
        print("No overdue tasks.")
        return
    for t in overdue:
        print(f"  #{t['id']} {t['title']} (was due: {t['due']})")


def main():
    args = sys.argv[1:]
    if not args:
        print("Commands: add <title> [priority] [due YYYY-MM-DD]")
        print("          complete <id> [id2]")
        print("          delete <id>")
        print("          list [done|pending] [priority]")
        print("          overdue")
        return

    cmd = args[0]

    if cmd == "add":
        if len(args) < 2:
            print("Usage: add <title> [priority] [due YYYY-MM-DD]")
            return
        title = args[1]
        priority = args[2] if len(args) > 2 else "medium"
        due = args[3] if len(args) > 3 else None
        add_task(title, priority, due)

    elif cmd == "complete":
        if len(args) < 2:
            print("Usage: complete <id> [id2]")
            return
        complete_task(*[int(a) for a in args[1:]])

    elif cmd == "delete":
        delete_task(int(args[1]))

    elif cmd == "list":
        status = args[1] if len(args) > 1 else None
        priority = args[2] if len(args) > 2 else None
        list_tasks(status, priority)

    elif cmd == "overdue":
        show_overdue()

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
