import requests
import random
from bs4 import BeautifulSoup

BASE_URL = "https://m-fur.ru/publications/?cpage="

def get_random_furry_image():
    page = random.randint(1, 24)
    url = BASE_URL + str(page)

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/123.0.0.0 Safari/537.36"
    }

    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        print(f"Ошибка {resp.status_code} при загрузке {url}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    images = []

    for img_tag in soup.select("a.img_link img"):
        img_url = img_tag.get("src")
        if img_url and img_url.startswith("http"):
            images.append(img_url)

    if not images:
        print(f"Картинок не найдено на странице {page}")
        return None

    return random.choice(images)


if __name__ == "__main__":
    print(get_random_furry_image())