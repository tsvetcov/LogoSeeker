import io
import os
import random
from locust import HttpUser, task, between
from PIL import Image

# Путь к папке с изображениями внутри контейнера Locust
IMAGES_DIR = "/mnt/locust/test_images"

class LogoSeekerFolderUser(HttpUser):
    wait_time = between(0.5, 1.5)

    def on_start(self):
        """Выполняется при старте каждого пользователя. Сканирует файлы."""
        self.image_files = []
        
        # Проверяем, существует ли папка и есть ли в ней файлы
        if os.path.exists(IMAGES_DIR):
            valid_extensions = ('.png', '.jpg', '.jpeg', '.webp')
            self.image_files = [
                f for f in os.listdir(IMAGES_DIR) 
                if f.lower().endswith(valid_extensions)
            ]

        if self.image_files:
            print(f"[+] Успешно найдено изображений для теста: {len(self.image_files)}")
        else:
            print("[!] Папка с картинками пуста или не найдена. Включен режим генерации в памяти.")
            # Дефолтный синий квадрат на случай, если папка пуста
            img = Image.new('RGB', (200, 200), color='blue')
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            self.fallback_image = img_byte_arr.getvalue()

    @task
    def send_random_logo(self):
        """Выбирает случайную картинку из папки и отправляет в FastAPI"""
        if self.image_files:
            # Выбираем случайный файл из списка
            random_filename = random.choice(self.image_files)
            full_path = os.path.join(IMAGES_DIR, random_filename)
            
            with open(full_path, "rb") as img_file:
                file_bytes = img_file.read()
                filename_to_send = random_filename
        else:
            # Иначе берем дефолтную заглушку
            file_bytes = self.fallback_image
            filename_to_send = "fallback_logo.png"

        # Упаковываем и отправляем на бэкенд
        files = {
            "file": (filename_to_send, file_bytes, "image/png")
        }

        with self.client.post("/api/v1/moderate", files=files, catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Ошибка {response.status_code}: {response.text}")
