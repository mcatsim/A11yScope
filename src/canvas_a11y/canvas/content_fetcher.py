"""Fetch all content types from a Canvas course."""
import asyncio
from rich.progress import Progress, SpinnerColumn, TextColumn

from canvas_a11y.canvas.client import CanvasClient
from canvas_a11y.models import ContentItem, ContentType, FileItem


class ContentFetcher:
    def __init__(self, client: CanvasClient, course_id: int):
        self.client = client
        self.course_id = course_id
        self.base = f"courses/{course_id}"

    async def fetch_all(self, progress: Progress | None = None) -> tuple[list[ContentItem], list[FileItem]]:
        """Fetch all content and file items from the course."""
        content_items = []
        file_items = []

        fetchers = [
            ("Pages", self.fetch_pages),
            ("Assignments", self.fetch_assignments),
            ("Discussions", self.fetch_discussions),
            ("Announcements", self.fetch_announcements),
            ("Syllabus", self.fetch_syllabus),
            ("Quizzes", self.fetch_quizzes),
        ]

        for label, fetcher in fetchers:
            task = progress.add_task(f"Fetching {label}...", total=None) if progress else None
            try:
                items = await fetcher()
                content_items.extend(items)
            except Exception as e:
                # Log but continue - some content types may not be available
                if progress and task is not None:
                    progress.update(task, description=f"[yellow]{label}: {e}")
            finally:
                if progress and task is not None:
                    progress.update(task, completed=True)

        # Fetch files separately
        task = progress.add_task("Fetching Files...", total=None) if progress else None
        try:
            file_items = await self.fetch_files()
        except Exception:
            pass
        finally:
            if progress and task is not None:
                progress.update(task, completed=True)

        return content_items, file_items

    async def fetch_pages(self) -> list[ContentItem]:
        pages = await self.client.get_paginated(f"{self.base}/pages")
        items = []
        for page in pages:
            # Need to fetch individual page for body content
            detail = await self.client.get(f"{self.base}/pages/{page['url']}")
            items.append(ContentItem(
                id=page["page_id"],
                content_type=ContentType.PAGE,
                title=page.get("title", "Untitled Page"),
                url=page.get("html_url", ""),
                html_content=detail.get("body", ""),
            ))
        return items

    async def fetch_assignments(self) -> list[ContentItem]:
        assignments = await self.client.get_paginated(f"{self.base}/assignments")
        return [
            ContentItem(
                id=a["id"],
                content_type=ContentType.ASSIGNMENT,
                title=a.get("name", "Untitled Assignment"),
                url=a.get("html_url", ""),
                html_content=a.get("description", ""),
            )
            for a in assignments
        ]

    async def fetch_discussions(self) -> list[ContentItem]:
        topics = await self.client.get_paginated(f"{self.base}/discussion_topics")
        return [
            ContentItem(
                id=t["id"],
                content_type=ContentType.DISCUSSION,
                title=t.get("title", "Untitled Discussion"),
                url=t.get("html_url", ""),
                html_content=t.get("message", ""),
            )
            for t in topics
            if not t.get("is_announcement", False)
        ]

    async def fetch_announcements(self) -> list[ContentItem]:
        topics = await self.client.get_paginated(
            f"{self.base}/discussion_topics",
            params={"only_announcements": "true"},
        )
        return [
            ContentItem(
                id=t["id"],
                content_type=ContentType.ANNOUNCEMENT,
                title=t.get("title", "Untitled Announcement"),
                url=t.get("html_url", ""),
                html_content=t.get("message", ""),
            )
            for t in topics
        ]

    async def fetch_syllabus(self) -> list[ContentItem]:
        course = await self.client.get(f"{self.base}", params={"include[]": "syllabus_body"})
        body = course.get("syllabus_body", "")
        if not body:
            return []
        return [ContentItem(
            id=0,
            content_type=ContentType.SYLLABUS,
            title="Course Syllabus",
            url=course.get("html_url", "") + "/assignments/syllabus",
            html_content=body,
        )]

    async def fetch_quizzes(self) -> list[ContentItem]:
        quizzes = await self.client.get_paginated(f"{self.base}/quizzes")
        return [
            ContentItem(
                id=q["id"],
                content_type=ContentType.QUIZ,
                title=q.get("title", "Untitled Quiz"),
                url=q.get("html_url", ""),
                html_content=q.get("description", ""),
            )
            for q in quizzes
        ]

    async def fetch_files(self) -> list[FileItem]:
        files = await self.client.get_paginated(f"{self.base}/files")
        return [
            FileItem(
                id=f["id"],
                display_name=f.get("display_name", f.get("filename", "unknown")),
                filename=f.get("filename", "unknown"),
                content_type_header=f.get("content-type", f.get("mime_class", "")),
                size=f.get("size", 0),
                url=f.get("url", ""),
            )
            for f in files
        ]
