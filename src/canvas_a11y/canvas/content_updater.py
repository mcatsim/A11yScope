"""Update Canvas content with fixed HTML."""
from canvas_a11y.canvas.client import CanvasClient
from canvas_a11y.models import ContentItem, ContentType


class ContentUpdater:
    """Pushes fixed HTML content back to Canvas via the API."""

    def __init__(self, client: CanvasClient, course_id: int):
        self.client = client
        self.course_id = course_id
        self.base = f"courses/{course_id}"

    async def update_content(self, item: ContentItem, fixed_html: str) -> bool:
        """Update a content item's HTML in Canvas. Returns True on success."""
        updaters = {
            ContentType.PAGE: self._update_page,
            ContentType.ASSIGNMENT: self._update_assignment,
            ContentType.DISCUSSION: self._update_discussion,
            ContentType.ANNOUNCEMENT: self._update_discussion,  # same endpoint
            ContentType.SYLLABUS: self._update_syllabus,
            ContentType.QUIZ: self._update_quiz,
        }
        updater = updaters.get(item.content_type)
        if not updater:
            return False
        await updater(item, fixed_html)
        return True

    async def _update_page(self, item: ContentItem, html: str):
        await self.client.put(f"{self.base}/pages/{item.id}", json={"wiki_page": {"body": html}})

    async def _update_assignment(self, item: ContentItem, html: str):
        await self.client.put(f"{self.base}/assignments/{item.id}", json={"assignment": {"description": html}})

    async def _update_discussion(self, item: ContentItem, html: str):
        await self.client.put(f"{self.base}/discussion_topics/{item.id}", json={"message": html})

    async def _update_syllabus(self, item: ContentItem, html: str):
        await self.client.put(f"{self.base}", json={"course": {"syllabus_body": html}})

    async def _update_quiz(self, item: ContentItem, html: str):
        await self.client.put(f"{self.base}/quizzes/{item.id}", json={"quiz": {"description": html}})
