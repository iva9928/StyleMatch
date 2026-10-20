"""Safe Pillow helpers for validating clothing images and making thumbnails."""

from pathlib import Path

from PIL import Image, UnidentifiedImageError

SUPPORTED_IMAGE_FORMATS = {"PNG", "JPEG", "WEBP"}


class ImageValidationError(ValueError):
    """Raised when an image is missing, unreadable, or unsupported."""


def validate_image(path: str | Path) -> None:
    """Ensure a local image exists, can be decoded, and uses a supported format."""
    image_path = Path(path)
    if not image_path.is_file():
        raise ImageValidationError("The selected image file could not be found.")

    try:
        with Image.open(image_path) as image:
            if image.format not in SUPPORTED_IMAGE_FORMATS:
                raise ImageValidationError(
                    "Choose a PNG, JPEG, or WEBP image."
                )
            image.load()
    except ImageValidationError:
        raise
    except (
        Image.DecompressionBombError,
        OSError,
        UnidentifiedImageError,
        ValueError,
    ) as error:
        raise ImageValidationError(
            "The selected image is unreadable or damaged."
        ) from error


def create_thumbnail(
    path: str | Path,
    size: tuple[int, int],
) -> Image.Image:
    """Return a detached, proportion-preserving thumbnail from a supported image."""
    image_path = Path(path)
    if not image_path.is_file():
        raise ImageValidationError("The selected image file could not be found.")

    try:
        with Image.open(image_path) as image:
            if image.format not in SUPPORTED_IMAGE_FORMATS:
                raise ImageValidationError(
                    "Choose a PNG, JPEG, or WEBP image."
                )
            image.thumbnail(size, Image.Resampling.LANCZOS)
            return image.copy()
    except ImageValidationError:
        raise
    except (
        Image.DecompressionBombError,
        OSError,
        UnidentifiedImageError,
        ValueError,
    ) as error:
        raise ImageValidationError(
            "The selected image is unreadable or damaged."
        ) from error
