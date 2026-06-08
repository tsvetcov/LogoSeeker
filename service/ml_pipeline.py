import logging
from typing import Dict, Any

import cv2
import numpy as np
import json
from PIL import Image
from ultralytics import YOLO

from classifier.classifier import LogoClassifier
from classifier.utils import crop_bounding_box, resize_image, top_n_closest_embs
from classifier import config

logger = logging.getLogger(__name__)

class LogoPipeline:
    def __init__(self, detector_path: str = "best.pt", conf_threshold: float = 0.1):
        logger.info("Инициализация детектора YOLO (путь: %s)...", detector_path)
        self.detector = YOLO(detector_path)
        self.conf_threshold = conf_threshold

        logger.info("Инициализация классификатора (Embeddings)...")
        self.classifier = LogoClassifier()
        try:
            self.restricted_db = np.load(config.RESTRICTED_EMB_BASE_PATH)
            self.competitors_db = np.load(config.COMPETITORS_EMB_BASE_PATH)
            self.employers_db = np.load(config.EMPLOYERS_EMB_BASE_PATH)

            with open(config.RESTRICTED_EMB_MAP_PATH, "r") as f:
                self.restricted_db_map = json.load(f)
            with open(config.COMPETITORS_EMB_MAP_PATH, "r") as f:
                self.competitors_db_map = json.load(f)
            with open(config.EMPLOYERS_EMB_MAP_PATH, "r") as f:
                self.employers_db_map = json.load(f)
        except FileNotFoundError as e:
            logger.error(f'Неполный комплект файлов баз и мапинга: {e}')
            raise
        except json.JSONDecodeError as e:
            logger.error(f'Ошибка обработки json: {e}')
            raise
        logger.info(f'Эталоны эмбеддингов нежелательных логотипов загружены')


    def _search_with_mapping(self, emb, database, database_map, top_n=1):
        """
        Ищет top_n ближайших эмбеддингов в базе с маппингом

        Args:
            emb: анализируемый эмбеддинг (numpy array)
            database: матрциа с веекторами эталонов
            database_map: файл с мапингом
            top_n: количество ближайших соседей
            threshold: порог схожести (если указан, то результаты ниже порога отбрасываются)

        Returns:
            list of dict: [{'name': name, 'similarity': sim}, ...]
        """
        positions, similarities = top_n_closest_embs(emb, database, top_n)
        if len(positions) == 0:
            return []

        results = []
        for pos, sim in zip(positions, similarities):
            name = database_map.get(str(pos), database_map.get(pos, f"unknown_{pos}"))

            results.append({
                'name': name,
                'similarity': float(sim)
            })

        return results


    def _get_best_match(self, best_restricted_match, best_competitors_match, best_employers_match):
        """
        Выбирает лучший матч из трех списков по наибольшей схожести

        Args:
            best_restricted_match: list
            best_competitors_match: list
            best_employers_match: list
        Returns:
            dict: {
                'category': 'restricted' | 'competitor' | 'employer',
                'name': str,
                'similarity': float,
            }
        """
        all_matches = []

        if best_restricted_match:
            all_matches.append({
                'category': 'restricted',
                'name': best_restricted_match[0]['name'],
                'similarity': best_restricted_match[0]['similarity']
            })

        if best_competitors_match:
            all_matches.append({
                'category': 'competitor',
                'name': best_competitors_match[0]['name'],
                'similarity': best_competitors_match[0]['similarity']
            })

        if best_employers_match:
            all_matches.append({
                'category': 'employer',
                'name': best_employers_match[0]['name'],
                'similarity': best_employers_match[0]['similarity']
            })

        if not all_matches:
            return {'category': 'unknown', 'name': 'Unknown', 'similarity': 0.0}

        best = max(all_matches, key=lambda x: x['similarity'])
        return best


    def process_image(self, image_bytes: bytes) -> Dict[str, Any]:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img_cv is None:
            logger.error("Не удалось декодировать байты в изображение.")
            return {"status": "error", "message": "Не удалось прочитать изображение"}

        img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_rgb)

        results_data = []

        det_results = self.detector(img_pil, verbose=False, conf=0.10)

        for r in det_results:
            for box in r.boxes:
                det_conf = float(box.conf[0])

                if det_conf < self.conf_threshold:
                    continue

                coords_abs = box.xyxy[0].tolist()
                coords_yolo = box.xywhn[0].tolist()

                try:
                    crop_img = crop_bounding_box(img_pil, coords_abs)
                    processed_crop = resize_image(crop_img)

                    if isinstance(processed_crop, np.ndarray):
                        processed_crop = Image.fromarray(processed_crop)

                    embedding = self.classifier.get_embedding(processed_crop)

                    best_resricted_match = self._search_with_mapping(
                        embedding,
                        self.restricted_db,
                        self.restricted_db_map,
                        top_n=1,
                    )
                    best_competitors_match = self._search_with_mapping(
                        embedding,
                        self.competitors_db,
                        self.competitors_db_map,
                        top_n=1,
                    )
                    best_employers_match = self._search_with_mapping(
                        embedding,
                        self.employers_db,
                        self.employers_db_map,
                        top_n=1,
                    )

                    closest_match_data = self._get_best_match(
                        best_resricted_match,
                        best_competitors_match,
                        best_employers_match
                    )

                    best_match = closest_match_data['name']
                    similarity = closest_match_data['similarity']
                    logo_category = closest_match_data['category']
                    verdict = "ok"
                    if logo_category in ["restricted", "competitor"]:
                        if similarity >= config.AUTO_BLOCK_THRESHOLD:
                            verdict = "blocked"
                        elif similarity >= config.MANUAL_CHECK_THRESHOLD:
                            verdict = "manual_moderation"

                    results_data.append({
                        "box": [round(c, 4) for c in coords_yolo],
                        "detector_confidence": round(det_conf, 4),
                        "best_match": best_match,
                        "similarity_score": round(similarity, 4),
                        "verdict": verdict
                    })

                except Exception as e:
                    logger.warning("Ошибка при обработке кропа: %s", e)
                    continue

        return {
            "status": "success",
            "found_logos": len(results_data),
            "details": results_data
        }
