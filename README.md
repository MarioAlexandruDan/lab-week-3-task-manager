# Task Manager CLI

A minimal command-line task manager backed by a JSON file.

## Usage

```bash
python3 task_manager.py add <title> [priority] [due YYYY-MM-DD]
python3 task_manager.py list [done|pending] [priority]
python3 task_manager.py complete <id>
python3 task_manager.py delete <id>
python3 task_manager.py overdue
```

## Examples

```bash
python3 task_manager.py add "Buy milk" low 2026-01-01
python3 task_manager.py add "Fix bug" high 2026-05-10
python3 task_manager.py list pending
python3 task_manager.py list pending high
python3 task_manager.py complete 1
python3 task_manager.py overdue
```

## Priority levels

`low` · `medium` · `high`
