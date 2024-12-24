import requests
import json
import os
import logging
from tqdm import tqdm
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

VK_TOKEN = os.getenv('VK_TOKEN')
YA_TOKEN = os.getenv('YA_TOKEN')
USER_ID = os.getenv('USER_ID')
FOLDER_NAME = 'vk_photos'
PHOTO_COUNT = 5

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='vk_photos.log',
    filemode='w',
    encoding='utf-8'
)

# Добавляем обработчик для вывода логов в консоль
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(console_handler)


def create_folder_on_yandex_disk(folder_name):
    """
    Создает папку на Яндекс.Диске, если она не существует.
    """
    url = f"https://cloud-api.yandex.net/v1/disk/resources"
    headers = {
        'Authorization': f'OAuth {YA_TOKEN}'
    }
    params = {
        'path': folder_name
    }
    
    # Проверяем, существует ли папка
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        logging.info(f"Папка '{folder_name}' уже существует.")
        return  
    elif response.status_code == 404:
        # Папка не найдена, создаем ее
        response = requests.put(url, headers=headers, params=params)
        response.raise_for_status()  
        logging.info(f"Папка '{folder_name}' успешно создана.")
    else:
        response.raise_for_status()  


def get_photos(album_id):
    """
    Получает фотографии из указанного альбома пользователя VK.

    """
    url = 'https://api.vk.com/method/photos.get'
    params = {
        'owner_id': USER_ID,
        'album_id': album_id,
        'access_token': VK_TOKEN,
        'extended': 1,
        'photo_sizes': 1,
        'v': '5.131'
    }
    response = requests.get(url, params=params)
    response.raise_for_status() 
    
    if 'response' not in response.json():
        raise ValueError("В ответе отсутствует ключ 'response'. Проверьте параметры запроса.")

    return response.json()['response']['items']


def upload_to_yandex_disk(file_name, file_path, folder_name):
    """
    Загружает файл на Яндекс.Диск.
    
    Args:
        file_name (str): Имя файла для загрузки.
        file_path (str): Локальный путь к файлу.
        folder_name (str): Имя папки на Яндекс.Диске, куда будет загружен файл.
    """
    url = f'https://cloud-api.yandex.net/v1/disk/resources/upload'
    headers = {
        'Authorization': f'OAuth {YA_TOKEN}'
    }
    params = {
        'path': f"{folder_name}/{file_name}",
        'overwrite': 'true'
    }
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    upload_url = response.json()['href']
    
    with open(file_path, 'rb') as f:
        response = requests.put(upload_url, files={'file': f})
        response.raise_for_status()


def main():
    create_folder_on_yandex_disk(FOLDER_NAME)
    
    album_id = input("Введите ID альбома (например, 'profile' или 'wall'): ")
    photos = get_photos(album_id)
    
    sorted_photos = sorted(photos, key=lambda x: max(s['width'] * s['height'] for s in x['sizes']), reverse=True)
    selected_photos = sorted_photos[:PHOTO_COUNT]
    photo_info = []
    
    for photo in tqdm(selected_photos, desc="Загрузка фотографий", unit="фото"):
        max_size = max(photo['sizes'], key=lambda x: x['width'] * x['height'])
        
        likes_count = photo.get('likes', {}).get('count', 0)
        file_name = f"{likes_count if likes_count > 0 else 'no_likes'}.jpg"
        file_path = f"./{file_name}"

        img_data = requests.get(max_size['url']).content
        with open(file_path, 'wb') as img_file:
            img_file.write(img_data)

        upload_to_yandex_disk(file_name, file_path, FOLDER_NAME)
        
        photo_info.append({
            'file_name': file_name,
            'size': max_size['type']
        })

        os.remove(file_path)

    with open('photo_info.json', 'w', encoding='utf-8') as json_file:
        json.dump(photo_info, json_file, ensure_ascii=False, indent=4)
    
    logging.info("Информация о загруженных фотографиях сохранена в 'photo_info.json'.")


if __name__ == '__main__':
    main()

