import requests
import pandas as pd
from bs4 import BeautifulSoup
import shutil
import os
import time
from io import BytesIO
from PIL import Image


##GETTING DATA FROM THE API
URL = "https://api.artic.edu/api/v1/artworks/search?"
FIELDS = "id,title,artist_display,description,image_id,style_id"

def clean_desc(desc):
    soup = BeautifulSoup(desc, 'html.parser').get_text().strip()
    return soup

def data_collection(limit):
    params = {"query[exists][field]": "description",
              "fields": FIELDS,
              "limit": limit,

              }
    response = requests.get(url=URL, params=params)
    response.raise_for_status()
    data = response.json()['data']

    # desc cleaning
    cleaned_data = []
    for i in data:
        if not i.get('description') or not i.get("image_id"):
            continue
        else:
            cleaned_data.append({
                "id": i["id"],
                "title": i["title"],
                "artist": i["artist_display"],
                "description": clean_desc(i["description"]),
                "image_id": i["image_id"],
                "style_id": i['style_id']
            })

    return cleaned_data

artworks = data_collection(100)
dataframe = pd.DataFrame(artworks, columns=['id', 'title', 'artist', 'description', 'image_id', 'style_id'])
dataframe.head()



#MAKES DIRECTORY
os.makedirs("data/images", exist_ok=True)

#IMAGE DOWNLOAD
HEADERS = {
    "User-Agent": "art-description-project (pineapplegarden22@gmail.com)",
    "AIC-User-Agent": "art-description-project (pineapplegarden22@gmail.com)",
}

def download_image(image_id, save_path, size=843):
    url = f"https://www.artic.edu/iiif/2/{image_id}/full/{size},/0/default.jpg"
    response = requests.get(url, headers=HEADERS, timeout=30)
    if response.status_code != 200:
        print(f"FAILED {image_id}: HTTP {response.status_code}")
        return False
    img = Image.open(BytesIO(response.content)).convert("RGB")
    img.save(save_path)
    return True

os.makedirs("data/images", exist_ok=True)

ok = 0
for art in artworks:
    path = f"data/images/{art['id']}.jpg"
    if download_image(art["image_id"], path):
        ok += 1
    time.sleep(0.2)

print(f"Downloaded {ok}/{len(artworks)}")
print(len(os.listdir("data/images")), "files in folder")

ok = 0
for art in artworks:
    path = f"data/images/{art['id']}.jpg"
    if os.path.exists(path):          # skip ones already saved
        ok += 1
        continue
    if download_image(art["image_id"], path):
        ok += 1
    time.sleep(0.2)

print(f"Downloaded {ok}/{len(artworks)}")
print(len(os.listdir("data/images")), "files in folder")


####
##ADDITIONAL FEATURES
EXTRA = "id,date_display,medium_display,dimensions,style_title,classification_title,artwork_type_title,place_of_origin,is_public_domain,thumbnail"

def get_meta(art_id):
    r = requests.get(f"https://api.artic.edu/api/v1/artworks/{art_id}",
                     params={"fields": EXTRA}, headers=HEADERS, timeout=30)
    r.raise_for_status()
    d = r.json()["data"]
    return {
        "id": d["id"],
        "date": d.get("date_display"),
        "medium": d.get("medium_display"),
        "dimensions": d.get("dimensions"),
        "style": d.get("style_title"),
        "classification": d.get("classification_title"),
        "type": d.get("artwork_type_title"),
        "origin": d.get("place_of_origin"),
        "public_domain": d.get("is_public_domain"),
        "alt_text": (d.get("thumbnail") or {}).get("alt_text"),
    }

meta = []
for art_id in dataframe["id"]:
    meta.append(get_meta(art_id))
    time.sleep(0.3)

dataframe = dataframe.merge(pd.DataFrame(meta), on="id")
dataframe.to_csv("data/metadata.csv", index=False)
print(dataframe["alt_text"].notna().sum(), "have alt text;",
      dataframe["public_domain"].sum(), "public domain")


####

dataframe.to_csv("data/metadata.csv", index=False)

shutil.make_archive("art_data", "zip", "data")


print(len(os.listdir("data/images")), "images")
print(os.path.getsize("art_data.zip") / 1e6, "MB")

import os, requests
from io import BytesIO
from PIL import Image

HEADERS = {
    "User-Agent": "art-description-project (pineapplegarden22@gmail.com)",
    "AIC-User-Agent": "art-description-project (pineapplegarden22@gmail.com)",
}

print("working dir:", os.getcwd())
print("records in artworks:", len(artworks))

os.makedirs("data/images", exist_ok=True)

art = artworks[0]
url = f"https://www.artic.edu/iiif/2/{art['image_id']}/full/843,/0/default.jpg"
print("url:", url)

r = requests.get(url, headers=HEADERS, timeout=30)
print("status:", r.status_code, "| type:", r.headers.get("content-type"), "| bytes:", len(r.content))

if r.status_code == 200:
    Image.open(BytesIO(r.content)).convert("RGB").save(f"data/images/{art['id']}.jpg")
    print("saved:", os.listdir("data/images"))
else:
    print(r.text[:300])