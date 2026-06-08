import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ml_pipeline import LogoPipeline
import database

logger = logging.getLogger("uvicorn.error")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Инициализация ML-моделей...")
    app.state.pipeline = LogoPipeline(detector_path="best.pt")
    logger.info("Модели успешно загружены.")

    yield

    logger.info("Очистка ресурсов...")
    del app.state.pipeline

app = FastAPI(title="LogoSeeker API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/v1/history")
def get_history(limit: int = 50, db: Session = Depends(database.get_db)):
    """Возвращает историю последних проверок (от новых к старым)"""
    try:
        logs = db.query(database.ModerationLog)\
                 .order_by(desc(database.ModerationLog.created_at))\
                 .limit(limit)\
                 .all()
        return logs
    except Exception as e:
        logger.exception("Ошибка при получении истории")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Не удалось получить историю."
        ) 

@app.post("/api/v1/moderate")
async def moderate_image(
    file: UploadFile = File(...), 
    db: Session = Depends(database.get_db)
):
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, 
            detail="Поддерживаются только изображения."
        )

    try:
        image_bytes = await file.read()
        pipeline: LogoPipeline = app.state.pipeline

        ml_result = pipeline.process_image(image_bytes)

        overall_status = "ok"
        best_match = "None"
        max_sim = 0.0

        for detail in ml_result.get("details", []):
            if detail["similarity_score"] > max_sim:
                max_sim = detail["similarity_score"]
                best_match = detail["best_match"]

            verdict = detail.get("verdict", "ok")
            if verdict == "blocked":
                overall_status = "blocked"
            elif verdict == "manual_moderation" and overall_status != "blocked":
                overall_status = "manual_moderation"

        db_log = database.ModerationLog(
            filename=file.filename,
            overall_status=overall_status,
            found_logos=ml_result.get("found_logos", 0),
            best_match=best_match,
            max_similarity=max_sim
        )
        db.add(db_log)
        db.commit()
        db.refresh(db_log) # Получаем сгенерированный базой ID

        ml_result["overall_status"] = overall_status
        ml_result["db_record_id"] = db_log.id

        return ml_result

    except Exception as e:
        logger.exception("Ошибка при обработке изображения")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Внутренняя ошибка сервера."
        )