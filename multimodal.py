import base64
import io
from PIL import Image
from typing import Optional, Tuple

class ImageProcessor:
    def __init__(self, max_size: Tuple[int, int] = (1024, 1024)):
        self.max_size = max_size

    def validate_image(self, file) -> bool:
        """Validate if the uploaded file is a supported image"""
        if file is None:
            return False

        supported_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        return file.type in supported_types

    def resize_image(self, file, max_size: Optional[Tuple[int, int]] = None) -> bytes:
        """Resize image to reduce file size while maintaining aspect ratio"""
        if max_size is None:
            max_size = self.max_size

        image = Image.open(file)
        image.thumbnail(max_size, Image.Resampling.LANCZOS)

        # Save to bytes
        output = io.BytesIO()
        image.save(output, format=image.format or 'JPEG')
        return output.getvalue()

    def convert_to_base64(self, image_bytes: bytes) -> str:
        """Convert image bytes to base64 string"""
        return base64.b64encode(image_bytes).decode('utf-8')

    def process_uploaded_image(self, file) -> Optional[str]:
        """Process uploaded image file and return base64 string"""
        if not self.validate_image(file):
            return None

        try:
            resized_bytes = self.resize_image(file)
            return self.convert_to_base64(resized_bytes)
        except Exception as e:
            print(f"Error processing image: {e}")
            return None

    def create_image_message(self, text: str, image_base64: str, model_name: str) -> dict:
        """Create a message dict with image content for API calls"""
        # Different models may have different image formats
        lower_name = model_name.lower()
        vision_keywords = ["vision", "scout-17b", "llama-4-scout"]
        if any(keyword in lower_name for keyword in vision_keywords):
            return {
                "role": "user",
                "content": [
                    {"type": "text", "text": text},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            }
        else:
            # Fallback for non-vision models: do not send image content
            return {
                "role": "user",
                "content": text
            }

    def get_image_info(self, file) -> dict:
        """Get information about the uploaded image"""
        if not self.validate_image(file):
            return {}

        try:
            image = Image.open(file)
            return {
                "format": image.format,
                "size": image.size,
                "mode": image.mode,
                "filename": file.name
            }
        except Exception as e:
            return {"error": str(e)}#</content>
#<parameter name="filePath">/home/daddywu/Python區/GenAI_class/multimodal.py