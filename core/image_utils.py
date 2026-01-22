"""Image processing utilities for automatic resizing."""
import os
from io import BytesIO
from PIL import Image
from django.core.files.base import ContentFile


def resize_image(image_field, max_width=1200, max_height=800, quality=85):
    """
    Resize an image to fit within max dimensions while maintaining aspect ratio.

    Args:
        image_field: Django ImageField instance
        max_width: Maximum width in pixels
        max_height: Maximum height in pixels
        quality: JPEG quality (1-100)

    Returns:
        ContentFile with resized image, or None if no resize needed
    """
    if not image_field:
        return None

    try:
        img = Image.open(image_field)
    except Exception:
        return None

    # Convert RGBA to RGB if necessary (for JPEG)
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')

    # Get original dimensions
    original_width, original_height = img.size

    # Check if resize is needed
    if original_width <= max_width and original_height <= max_height:
        return None

    # Calculate new dimensions maintaining aspect ratio
    ratio = min(max_width / original_width, max_height / original_height)
    new_width = int(original_width * ratio)
    new_height = int(original_height * ratio)

    # Resize using high-quality resampling
    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # Save to buffer
    buffer = BytesIO()
    img.save(buffer, format='JPEG', quality=quality, optimize=True)
    buffer.seek(0)

    # Generate new filename with .jpg extension
    original_name = os.path.splitext(os.path.basename(image_field.name))[0]
    new_filename = f"{original_name}.jpg"

    return ContentFile(buffer.read(), name=new_filename)


def process_uploaded_image(instance, field_name, max_width=1200, max_height=800):
    """
    Process an uploaded image on a model instance.
    Call this in the model's save() method.

    Args:
        instance: Model instance
        field_name: Name of the ImageField
        max_width: Maximum width in pixels
        max_height: Maximum height in pixels
    """
    image_field = getattr(instance, field_name)
    if not image_field:
        return

    # Check if this is a new upload by seeing if we can access the file
    try:
        image_field.file.seek(0)
    except (ValueError, AttributeError):
        # File already saved, skip processing
        return

    resized = resize_image(image_field, max_width, max_height)
    if resized:
        # Replace the image with the resized version
        image_field.save(resized.name, resized, save=False)
