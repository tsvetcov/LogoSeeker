import os
os.environ["TORCH_FORCE_WEIGHTS_ONLY_LOAD"] = "0"
import torch
torch.serialization.add_safe_globals([torch.get_default_dtype])
import ultralytics
torch.serialization.add_safe_globals([ultralytics.nn.tasks.DetectionModel])
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from ml_pipeline import LogoPipeline

logger = logging.getLogger("uvicorn.error")

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pipeline = LogoPipeline()
    yield
    del app.state.pipeline

app = FastAPI(title="LogoSeeker API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/v1/moderate")
async def moderate_image(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Файл должен быть изображением")

    try:
        image_bytes = await file.read()
        pipeline: LogoPipeline = app.state.pipeline

        ml_result = pipeline.process_image(image_bytes)

        overall_status = "ok"

        for detail in ml_result.get("details", []):
            verdict = detail.get("verdict", "ok")
            if verdict == "blocked":
                overall_status = "blocked"
            elif verdict == "manual_moderation" and overall_status != "blocked":
                overall_status = "manual_moderation"

        ml_result["overall_status"] = overall_status

        return ml_result

    except Exception as e:
        logger.error(f"Ошибка при обработке изображения {file.filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка сервера: {str(e)}")
