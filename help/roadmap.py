from collections import Counter
from dataclasses import dataclass
from datetime import date
from enum import Enum
from pathlib import Path

from whatnext.models import MarkdownFile, State


class RoadmapState(Enum):
    AVAILABLE = 1
    IN_PROGRESS = 2
    PLANNED = 3


@dataclass
class RoadmapTask:
    text: str
    state: State
    dependencies: list[str]


@dataclass
class RoadmapEntry:
    title: str
    description: str
    tasks: list[RoadmapTask]


def parse_roadmap_file(path: Path) -> RoadmapEntry:
    """Parse a roadmap task file and extract title, description, and tasks."""
    md_file = MarkdownFile(source=str(path), today=date.today())

    title = ""
    for task in md_file.tasks:
        if task.heading:
            # Extract title from heading like "# Title" or "# Parent / Title"
            title = task.heading.lstrip("# ").split(" / ")[-1]
            break

    # Extract description from file content (text between heading and first task)
    lines = path.read_text().splitlines()
    description_lines = []
    in_description = False
    for line in lines:
        if line.startswith("# "):
            in_description = True
            continue
        if in_description:
            if line.startswith("- ["):
                break
            description_lines.append(line)

    description = "\n".join(description_lines).strip("\n")

    tasks = [
        RoadmapTask(
            text=task.text,
            state=task.state,
            dependencies=task.deferred or [],
        )
        for task in md_file.tasks
    ]

    return RoadmapEntry(title=title, description=description, tasks=tasks)


def count_completed_in_path(path: str) -> tuple[int, int]:
    """Count completed and total tasks in a file or directory."""
    p = Path(path)

    if p.is_dir():
        completed = 0
        total = 0
        for md_file in p.glob("*.md"):
            c, t = count_completed_in_path(str(md_file))
            completed += c
            total += t
        return completed, total

    if not p.exists() or not p.is_file():
        return 0, 0

    md_file = MarkdownFile(source=str(p), today=date.today())
    counts = Counter(task.state for task in md_file.tasks)
    completed = counts.get(State.COMPLETE, 0)
    total = sum(counts.values())
    return completed, total


def calculate_task_progress(task: RoadmapTask) -> tuple[int, int]:
    """Calculate progress for a single task including itself and dependencies."""
    dep_completed = 0
    dep_total = 0
    for dep in task.dependencies:
        c, t = count_completed_in_path(dep)
        dep_completed += c
        dep_total += t
    total = 1 + dep_total
    # A roadmap task cannot be complete when dependencies are unsatisfied,
    # no matter what the task file says.
    if task.state == State.COMPLETE and dep_completed == dep_total:
        completed = 1 + dep_completed
    else:
        completed = dep_completed
    return completed, total


def generate_roadmap_markdown(roadmap_dir: Path) -> str:
    """Generate markdown content for the roadmap page."""
    from django.conf import settings
    from django.template.loader import get_template

    base_dir = settings.BASE_DIR

    entries = []

    for md_file in roadmap_dir.glob("*.md"):
        entry = parse_roadmap_file(md_file)
        entry_state = RoadmapState.PLANNED

        tasks = []
        for task in entry.tasks:
            completed, total = calculate_task_progress(task)
            if completed == total:
                task_state = RoadmapState.AVAILABLE
            elif completed > 0:
                task_state = RoadmapState.IN_PROGRESS
            else:
                task_state = RoadmapState.PLANNED
            if task_state.value < entry_state.value:
                entry_state = task_state
            if task_state == RoadmapState.AVAILABLE:
                status = "**Available**"
            elif task_state == RoadmapState.IN_PROGRESS:
                status = "_In Progress_"
            else:
                status = "Planned"
            task_url = ""
            if task.dependencies:
                dep_path = Path(task.dependencies[0])
                if dep_path.is_relative_to(base_dir):
                    relative_path = dep_path.relative_to(base_dir)
                    task_url = f"https://github.com/your5e/your5e/blob/main/{relative_path}"

            tasks.append({
                "text": task.text,
                "status": status,
                "completed": completed,
                "total": total,
                "url": task_url,
            })

        entries.append({
            "title": entry.title,
            "description": entry.description,
            "state": entry_state,
            "tasks": tasks,
        })

    # Sort: available first, then in progress, then planned; alphabetical within
    entries.sort(key=lambda e: (e["state"].value, e["title"].lower()))

    template = get_template("help/roadmap.md")
    return template.render({"entries": entries})
