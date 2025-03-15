import os
import requests
from fastapi import FastAPI, UploadFile, File, HTTPException
from ultralytics import YOLO
from pymongo import MongoClient
import logging
from typing import Dict
from colorama import init, Fore, Style
from dotenv import load_dotenv
import json
import cv2
import numpy as np
from tensorflow.keras.models import load_model

load_dotenv()
OLLAMA_URL = "http://localhost:11434/api/generate"

init(autoreset=True)
class ColoredFormatter(logging.Formatter):
    LOG_COLORS = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.MAGENTA
    }
    def format(self, record):
        color = self.LOG_COLORS.get(record.levelno, Fore.WHITE)
        record.levelname = f"{color}{record.levelname}{Style.RESET_ALL}"
        record.msg = f"{color}{record.msg}{Style.RESET_ALL}"
        return super().format(record)

handler = logging.StreamHandler()
handler.setFormatter(ColoredFormatter("%(asctime)s - %(levelname)s - %(message)s"))
logger = logging.getLogger(__name__)
logger.handlers.clear()
logger.addHandler(handler)
logger.setLevel(logging.INFO)

app = FastAPI()
model = YOLO("yolov8n.pt")
client = MongoClient("mongodb://localhost:27017/")
db = client["smartscene"]
knowledge_base = db["objects"]

def init_knowledge_base():
    if knowledge_base.count_documents({}) == 0:
        knowledge_base.insert_many([
            {"name": "person", "info": "Represents individuals, often central to scenes, suggesting focus or importance."},
            {"name": "weapon", "info": "Indicates combat, defense, or conflict scenarios."},
            {"name": "car", "info": "Suggests mobility, travel, or a chase scene."},
            {"name": "building", "info": "Provides a setting, often indicating urban or residential context."},
            {"name": "dog", "info": "Represents companionship or domestic life."},
            {"name": "table", "info": "A surface for gathering or objects, symbolizing community or activity."},
            {"name": "chair", "info": "A piece of furniture for seating, indicating a place for rest or gathering."}
        ])

init_knowledge_base()

# Load CNN
try:
    cnn_model = load_model('cnn_model.keras')
except:
    logger.error("CNN model not found. Please train using train_cnn.py.")
    raise HTTPException(status_code=500, detail="CNN model not found")

def preprocess_roi(image_path, box):
    img = cv2.imread(image_path)
    logger.info(f"box.xyxy: {box.xyxy}")
    xyxy = box.xyxy.cpu().numpy() if hasattr(box.xyxy, 'cpu') else box.xyxy.numpy()
    logger.info(f"xyxy.numpy(): {xyxy}")
    if xyxy.shape[0] == 0:
        logger.error("No valid coordinates in xyxy")
        return np.zeros((1, 32, 32, 3), dtype=np.float32)
    x1, y1, x2, y2 = map(int, xyxy[0])
    logger.info(f"Coordinates: x1={x1}, y1={y1}, x2={x2}, y2={y2}")
    height = y2 - y1
    width = x2 - x1
    aspect_ratio = height / width if width > 0 else 1
    if y2 <= y1 or x2 <= x1 or y2 > img.shape[0] or x2 > img.shape[1] or height < 10 or width < 10 or (aspect_ratio < 1.5 and "person" in model.names[int(box.cls[0].item())]):
        logger.warning(f"Invalid or non-person ROI: height={height}, width={width}, aspect_ratio={aspect_ratio}")
        return np.zeros((1, 32, 32, 3), dtype=np.float32)
    roi = img[y1:y2, x1:x2]
    logger.info(f"ROI shape before resize: {roi.shape}")
    roi = cv2.resize(roi, (32, 32))
    roi = roi.astype('float32') / 255.0
    logger.info(f"ROI shape after resize: {roi.shape}")
    return np.expand_dims(roi, axis=0)

class_labels = ["person", "others"]
cnn_to_kb = {
    0: "person",
    1: "others"
}

@app.post("/analyze")
async def analyze_image(file: UploadFile = File(...)):
    image_path = f"temp_{file.filename}"
    try:
        with open(image_path, "wb") as f:
            f.write(await file.read())
        
        logger.info("Analyzing image: %s", image_path)
        results = model.predict(source=image_path, conf=0.3)  # Lower confidence threshold
        detected_objects = {}
        classifications = {}
        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls[0].item())
                cls_name = model.names[cls_id]
                detected_objects[cls_name] = detected_objects.get(cls_name, 0) + 1
                logger.info(f"Detected: {cls_name}, box: {box.xyxy}")
                roi = preprocess_roi(image_path, box)
                if not np.all(roi == 0):  # Only predict if ROI is valid
                    logger.info(f"ROI shape for prediction: {roi.shape}")
                    prediction = cnn_model.predict(roi)
                    logger.info(f"Prediction shape: {prediction.shape}, values: {prediction}")
                    class_idx = np.argmax(prediction) if prediction.ndim == 1 else np.argmax(prediction, axis=1)[0]
                    logger.info(f"Class index: {class_idx}")
                    kb_class = cnn_to_kb.get(class_idx, "unknown")
                    if kb_class == "others" and cls_name.lower() in ["weapon", "car", "building", "dog", "table", "chair"]:
                        kb_class = cls_name.lower()
                    classifications[cls_name] = kb_class
                else:
                    classifications[cls_name] = "unknown"

        logger.info(f"Detected objects: {detected_objects}")
        logger.info(f"Classifications: {classifications}")
        context = []
        for obj in detected_objects.keys():
            info = knowledge_base.find_one({"name": obj.lower()})
            if info:
                context.append(f"{obj}: {info['info']}")
        context_text = "\n".join(context) if context else "No context available."
        analysis = "\n".join([f"{obj}: {count} (classified as {classifications.get(obj, 'unknown')})" for obj, count in detected_objects.items()])
        logger.info(f"Analysis: {analysis}")
        logger.info(f"Context: {context_text}")

        payload = {
            "model": "mistral",
            "prompt": f"Given this image analysis: {analysis} and context: {context_text}, provide a concise explanation of what the image might signify.",
            "max_tokens": 100,
            "temperature": 0.7,
            "top_p": 0.9
        }
        logger.info("Sending request to Ollama LLM...")
        response = requests.post(OLLAMA_URL, json=payload, stream=True)
        if response.status_code != 200:
            logger.error("LLM request failed: %s", response.text)
            raise HTTPException(status_code=500, detail=f"LLM error: {response.text}")
        
        commentary = ""
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line.decode('utf-8'))
                    if "response" in data:
                        commentary += data["response"]
                    logger.info(f"Ollama raw response chunk: {data}")
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {e}")
        
        commentary = commentary.strip()
        logger.info("Commentary generated successfully")
        return {"commentary": commentary}
    
    except Exception as e:
        logger.error("Error: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Analysis failed")
    
    finally:
        if os.path.exists(image_path):
            os.remove(image_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)