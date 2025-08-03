from ultralytics import YOLO
from functools import lru_cache


@lru_cache(maxsize=None)
def load_yolo_model(model_path="yolov8s.pt"):
    """Загружает модель YOLO и кэширует её."""
    return YOLO(model_path)
