import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4-vision-preview")
        self.max_image_size = int(os.getenv("MAX_IMAGE_SIZE", "4194304"))
        self.confidence_threshold = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))
        self.max_detections = int(os.getenv("MAX_DETECTIONS", "10"))
        self.padding_factor = float(os.getenv("PADDING_FACTOR", "1.2"))
        self.stacking_factor = float(os.getenv("STACKING_FACTOR", "0.85"))


settings = Settings()
