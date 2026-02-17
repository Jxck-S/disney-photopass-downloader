import json
import random
import string
import uuid
from datetime import datetime, timedelta

def random_string(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def random_id(length=8):
    return ''.join(random.choices(string.digits, k=length))

def random_date():
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2026, 12, 31)
    time_between_dates = end_date - start_date
    days_between_dates = time_between_dates.days
    random_number_of_days = random.randrange(days_between_dates)
    random_date = start_date + timedelta(days=random_number_of_days)
    return random_date.strftime("%Y-%m-%dT%H:%M:%SZ")

def randomize_data(data):
    if isinstance(data, dict):
        new_data = {}
        for key, value in data.items():
            if key == "encounters" and isinstance(value, list) and value and isinstance(value[0], str):
                 # MetaData encounters list (list of IDs)
                 new_data[key] = [str(uuid.uuid4()) for _ in value]
            elif key == "encounters" and isinstance(value, list):
                # guestMedia encounters
                new_data[key] = [randomize_encounter(item) for item in value]
            elif key in ["mlids", "resorts", "parks"]:
                # Keep these somewhat realistic or generic
                 new_data[key] = value # Keep structure but maybe randomize content if specific
            else:
                new_data[key] = randomize_value(key, value)
        return new_data
    return data

def randomize_encounter(encounter):
    new_encounter = {}
    for key, value in encounter.items():
        if key == "mediaList":
            new_encounter[key] = [randomize_media(m) for m in value]
        elif key == "encounterId":
            new_encounter[key] = str(uuid.uuid4())
        elif key == "encounterEtag":
            new_encounter[key] = random_string(32)
        elif key == "encounterName":
            new_encounter[key] = "Disney Resort Encounter"
        elif key == "origPark":
            # Keep valid parks for the example to work with coordinates
            new_encounter[key] = random.choice(["BOARDWALK", "POLY", "MK", "EPCOT"])
        else:
            new_encounter[key] = value # Keep other fields structure
    return new_encounter

def randomize_media(media):
    new_media = {}
    media_id = random_id(10)
    for key, value in media.items():
        if key == "mediaId":
            new_media[key] = media_id
        elif key == "guestMediaId":
            new_media[key] = int(random_id(10))
        elif key == "captureDate":
            new_media[key] = random_date()
        elif key == "expirationDate":
             new_media[key] = random_date()
        elif key == "subjects":
            new_media[key] = ["Mickey Mouse", "Donald Duck"]
        elif key in ["mediaThumb", "mediaMedium"]:
            if value:
                new_uri = f"https://example.com/media/{media_id}/{key}.jpg"
                new_media[key] = value.copy()
                new_media[key]["uri"] = new_uri
                new_media[key]["renditionType"] = key + "_wm"
            else:
                 new_media[key] = None
        elif key == "uri": # If it exists directly
             new_media[key] = f"https://example.com/media/{media_id}/full.jpg"
        else:
            new_media[key] = value
    return new_media

def randomize_value(key, value):
    if key in ["lastCapture"]:
        return random_date()
    return value

try:
    with open('photos.json', 'r') as f:
        data = json.load(f)

    randomized_data = randomize_data(data)

    with open('photos_example.json', 'w') as f:
        json.dump(randomized_data, f, indent=4)
    print("Successfully created randomized photos_example.json")

except Exception as e:
    print(f"Error: {e}")
