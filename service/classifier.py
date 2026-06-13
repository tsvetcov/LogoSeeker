import torch
import torch.nn as nn
import timm
from peft import LoraConfig, get_peft_model
import torchvision.transforms as transforms
from PIL import Image
import numpy as np
import config


class LogoClassifier(nn.Module):
    def __init__(self):
        super().__init__()
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        backbone = timm.create_model(config.CLASSIFIER_BACKBONE_NAME,
                                     pretrained=False,
                                     num_classes=0,
                                     img_size=config.CLASSIFIER_PIC_SIZE_MAX)
        # if hasattr(backbone, 'patch_embed'):
        #     backbone.patch_embed.img_size = (
        #         config.CLASSIFIER_PIC_SIZE_MAX,
        #         config.CLASSIFIER_PIC_SIZE_MAX
        #     )
        lora_config = LoraConfig(
            r=config.CLASSIFIER_LORA_R,
            lora_alpha=config.CLASSIFIER_LORA_ALPHA,
            target_modules=config.CLASSIFIER_LORA_TARGET_MODULES,
            lora_dropout=config.CLASSIFIER_LORA_DROPOUT,
        )
        self.backbone = get_peft_model(backbone, lora_config)

        self.projection = nn.Sequential(
            nn.Linear(config.CLASSIFIER_EMBEDDING_SIZE, 512),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(512, 384),
        )

        checkpoint = torch.load(config.CLASSIFIER_PATH, map_location=self.device)
        self.load_state_dict(checkpoint, strict=False)
        self.to(self.device)
        self.eval()

        self.transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=config.IMAGE_MEAN, std=config.IMAGE_STD),
        ])


    def get_embedding(self, image):
        """
        Возвращает нормализованный эмбеддинг
        Args:
            image (PIL.IMAGE): Изображение для получения эмбеддинга
        Returns:
            embedding (np.array): Полученный эмбеддинг
        """
        tensor = self.transform(image).unsqueeze(0)  # (1, 3, H, W)
        tensor = tensor.to(self.device)
        with torch.no_grad():
            features = self.backbone(tensor)
            embedding = self.projection(features)
            embedding = embedding / (torch.norm(embedding, dim=1, keepdim=True) + 1e-8)

        return embedding.squeeze().detach().cpu().numpy()

if __name__ == '__main__':
    import os

    if os.path.exists(config.CLASSIFIER_TEST_IMAGE_PATH):
        print('ТЕстовое изображение найдено')
        image = Image.open(config.CLASSIFIER_TEST_IMAGE_PATH)
        print(image.size)
    else:
        print('Тестируем на картине Малевича')
        image = Image.new(
            'RGB',
            (config.CLASSIFIER_PIC_SIZE_MAX, config.CLASSIFIER_PIC_SIZE_MAX),
            (0, 0, 0))
    print('Тест классификатора')
    try:
        model = LogoClassifier()
    except Exception as e:
        print(f'Ошибка {e} при загрузке модели')
        exit(1)

    try:
        embedding = model.get_embedding(image)
    except Exception as e:
        print(f'Ошибка {e} при получении эмбеддинга')

    print(f'emb_dim:{len(embedding)}')
    print(f'Первые пять элементов эмбеддингов {embedding[0:5]}')
    print(f'emb_vector_length:{np.linalg.norm(embedding)}')
