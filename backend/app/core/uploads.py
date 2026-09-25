from dataclasses import dataclass
from io import BytesIO
import warnings

from PIL import Image, UnidentifiedImageError

from app.core.errors import AppError

ALLOWED_IMAGE_MIMES = frozenset({"image/jpeg", "image/png", "image/webp"})
MAGIC = {"image/jpeg": (b"\xff\xd8\xff",), "image/png": (b"\x89PNG\r\n\x1a\n",), "image/webp": (b"RIFF",)}
FORMATS = {"image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WEBP"}
MAX_PIXELS = 30_000_000


@dataclass(frozen=True)
class UploadPolicy:
    max_bytes: int

    def validate(self, content_type: str, data: bytes) -> None:
        if content_type not in ALLOWED_IMAGE_MIMES:
            raise AppError(415, "unsupported_media_type", "Upload a JPG, PNG, or WebP image.")
        if len(data) > self.max_bytes:
            raise AppError(413, "upload_too_large", "Image exceeds the upload limit.")
        if not any(data.startswith(prefix) for prefix in MAGIC[content_type]):
            raise AppError(415, "invalid_image", "Image content does not match its type.")
        if content_type == "image/webp" and data[8:12] != b"WEBP":
            raise AppError(415, "invalid_image", "Image content does not match its type.")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(data)) as decoded:
                    if decoded.format != FORMATS[content_type] or decoded.width * decoded.height > MAX_PIXELS:
                        raise AppError(415, "invalid_image", "Image content does not match its type or exceeds the pixel limit.")
                    decoded.verify()
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
            raise AppError(415, "invalid_image", "Image could not be decoded safely.") from exc
