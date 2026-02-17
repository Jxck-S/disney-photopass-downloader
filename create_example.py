import json
import random
import string
import uuid
import re
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

def random_string(length=10, charset=string.ascii_letters + string.digits):
    return ''.join(random.choices(charset, k=length))

def random_digits(length=10):
    return ''.join(random.choices(string.digits, k=length))

def random_hex(length=32):
    return ''.join(random.choices('0123456789abcdef', k=length))

def random_date_str(format_str="%Y-%m-%dT%H:%M:%SZ"):
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2026, 12, 31)
    time_between_dates = end_date - start_date
    days_between_dates = time_between_dates.days
    random_number_of_days = random.randrange(days_between_dates)
    random_date = start_date + timedelta(days=random_number_of_days)
    return random_date.strftime(format_str)

def randomize_url(url, encounter_id):
    if not url:
        return url
    
    parsed = urlparse(url)
    
    # 1. Keep Domain (netloc) - User requested "same domains"
    
    # 2. Randomize Path
    # Structure: /<encounterId>/<long_id>-<date>-<id>-DSC<num>_<type>.JPG
    path_parts = parsed.path.split('/')
    new_path = parsed.path
    
    if len(path_parts) > 2:
        # Replace encounter ID in path
        path_parts[1] = encounter_id
        
        # Randomize filename part if it looks like the standard format
        filename = path_parts[-1]
        # Regex to try and match the file pattern roughly
        # 25062524202231-78303009-20260118T141629-163439-DSC05854_thumb_wm.JPG
        match = re.match(r'(\d+)-(\d+)-(\d{8}T\d{6})-(\d+)-(DSC\d+)(_.*)', filename)
        if match:
             part1 = random_digits(len(match.group(1)))
             part2 = random_digits(len(match.group(2)))
             part3 = random_date_str("%Y%m%dT%H%M%S") # Date in filename
             part4 = random_digits(len(match.group(4)))
             part5 = "DSC" + random_digits(4)
             part6 = match.group(6) # _thumb_wm.JPG (keep structure)
             new_filename = f"{part1}-{part2}-{part3}-{part4}-{part5}{part6}"
             path_parts[-1] = new_filename
        
        new_path = '/'.join(path_parts)

    # 3. Randomize Query Params (AWS stuff)
    qs = parse_qs(parsed.query)
    new_qs = {}
    for key, values in qs.items():
        val = values[0]
        if key == "X-Amz-Signature":
            new_qs[key] = random_hex(64)
        elif key == "X-Amz-Credential":
            # AKIA4YE2EIOD4Z4ISGEB/20260217/us-east-1/s3/aws4_request
            parts = val.split('/')
            if len(parts) > 1:
                parts[0] = random_string(20, string.ascii_uppercase + string.digits) # Access Key
                # parts[1] is date, could change but maybe keep for consistency?
            new_qs[key] = '/'.join(parts)
        elif key == "X-Amz-Date":
            new_qs[key] = datetime.now().strftime("%Y%m%dT%H%M%SZ")
        else:
            new_qs[key] = val # Keep headers, algorithm, expires mostly same or randomize if needed
            
    encoded_qs = urlencode(new_qs, doseq=True)
    
    # Reassemble
    return urlunparse((parsed.scheme, parsed.netloc, new_path, parsed.params, encoded_qs, parsed.fragment))

def randomize_media(media, encounter_id):
    new_media = media.copy()
    
    # Randomize IDs
    if "mediaId" in new_media:
        new_media["mediaId"] = random_digits(len(new_media["mediaId"]))
    if "guestMediaId" in new_media:
         # guestMediaId is int in JSON
        new_media["guestMediaId"] = int(random_digits(10))
        
    # Randomize Dates
    if "captureDate" in new_media:
        new_media["captureDate"] = random_date_str()
    if "expirationDate" in new_media:
        new_media["expirationDate"] = random_date_str()
    if "guestMediaModifiedDate" in new_media:
         new_media["guestMediaModifiedDate"] = random_date_str()

    # Randomize URLs in objects
    for key in ["mediaThumb", "mediaMedium", "mediaBase"]:
        if new_media.get(key):
            obj = new_media[key].copy()
            if "uri" in obj:
                obj["uri"] = randomize_url(obj["uri"], encounter_id)
            new_media[key] = obj
            
    return new_media

def randomize_encounter(encounter):
    new_encounter = encounter.copy()
    
    # 1. Randomize Encounter ID & Etag
    if "encounterId" in new_encounter:
        new_encounter["encounterId"] = str(uuid.uuid4())
    if "encounterEtag" in new_encounter:
        new_encounter["encounterEtag"] = random_hex(32)
        
    # 2. Preserve Park/Resort/Attraction (User Request)
    # "keep park resorts and origPark" "attaction names and ids keep tyhose"
    # So we DO NOT touch 'origPark', 'park', 'resort', 'attraction', 'attractionId', 'encounterName'
    
    # 3. Randomize Media List
    if "mediaList" in new_encounter:
        new_encounter["mediaList"] = [randomize_media(m, new_encounter.get("encounterId", "unknown")) for m in new_encounter["mediaList"]]
        
    return new_encounter

def process_json():
    try:
        with open('photos.json', 'r') as f:
            data = json.load(f)
            
        new_data = data.copy()
        
        # 1. Randomize top-level MetaData (if needed)
        if "metaData" in new_data:
            meta = new_data["metaData"].copy()
            if "encounters" in meta:
                # These are IDs corresponding to guestMedia encounters
                # We will generate them from the randomized encounters later to ensure consistency?
                # Actually, let's just randomize them now, it's just a list of strings
                 meta["encounters"] = [str(uuid.uuid4()) for _ in meta["encounters"]]
            if "lastCapture" in meta:
                meta["lastCapture"] = random_date_str()
            new_data["metaData"] = meta
            
        # 2. Randomize Guest Media
        if "guestMedia" in new_data and "encounters" in new_data["guestMedia"]:
            encounters = new_data["guestMedia"]["encounters"]
            new_encounters = [randomize_encounter(e) for e in encounters]
            
            # Sync metadata encounters list if it existed (optional but good for consistency)
            if "metaData" in new_data and "encounters" in new_data["metaData"]:
                 # Just make list of ids from new_encounters
                 new_data["metaData"]["encounters"] = [e["encounterId"] for e in new_encounters]
            
            new_data["guestMedia"]["encounters"] = new_encounters

        with open('photos_example.json', 'w') as f:
            json.dump(new_data, f, indent=4)
            
        print("Successfully created randomized photos_example.json with preserved park data.")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    process_json()
