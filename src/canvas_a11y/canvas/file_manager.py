"""Download and upload files via Canvas API (3-step upload)."""
import mimetypes
from pathlib import Path

from canvas_a11y.canvas.client import CanvasClient
from canvas_a11y.models import FileItem


class FileManager:
    """Manages file downloads and uploads for Canvas courses."""

    def __init__(self, client: CanvasClient, course_id: int, output_dir: Path):
        self.client = client
        self.course_id = course_id
        self.download_dir = output_dir / "downloads"
        self.remediated_dir = output_dir / "remediated"
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.remediated_dir.mkdir(parents=True, exist_ok=True)

    async def download_file(self, file_item: FileItem) -> Path:
        """Download a file from Canvas to the local downloads directory."""
        dest = self.download_dir / file_item.filename
        await self.client.download_file(file_item.url, dest)
        file_item.local_path = dest
        return dest

    async def upload_file(self, file_item: FileItem, local_path: Path, folder_path: str = "") -> dict:
        """Upload a file to Canvas using the 3-step upload process.

        Step 1: Notify Canvas of the upload (POST)
        Step 2: Upload the file to the provided URL
        Step 3: Confirm the upload
        """
        content_type = mimetypes.guess_type(str(local_path))[0] or "application/octet-stream"

        # Step 1: Request upload token
        step1 = await self.client.post(
            f"courses/{self.course_id}/files",
            json={
                "name": file_item.display_name,
                "size": local_path.stat().st_size,
                "content_type": content_type,
                "parent_folder_path": folder_path or "/",
                "on_duplicate": "overwrite",
            },
        )

        upload_url = step1["upload_url"]
        upload_params = step1.get("upload_params", {})

        # Step 2: Upload the file
        import httpx
        async with httpx.AsyncClient(follow_redirects=False) as upload_client:
            with open(local_path, "rb") as f:
                files = {"file": (file_item.display_name, f, content_type)}
                response = await upload_client.post(
                    upload_url,
                    data=upload_params,
                    files=files,
                )

            # Step 3: Confirm (follow the redirect or POST to confirm URL)
            if response.status_code in (301, 302, 303):
                confirm_url = response.headers["Location"]
                confirm_resp = await self.client._request("GET", confirm_url)
                return confirm_resp.json()

            return response.json()
