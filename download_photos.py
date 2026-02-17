import json
import os
import urllib.request
from urllib.error import HTTPError
from datetime import datetime
import fractions
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo # For older Python versions
import piexif

import platform
import time

def set_creation_time(path, timestamp):
    """
    Sets the file creation time on Windows.
    Falls back to os.utime on other systems (which sets modified/access time).
    """
    if platform.system() == 'Windows':
        try:
            import ctypes
            from ctypes import wintypes, byref

            # Define the required structures and constants
            FILE_WRITE_ATTRIBUTES = 0x0100
            OPEN_EXISTING = 3
            
            # CreateFileW signature
            CreateFileW = ctypes.windll.kernel32.CreateFileW
            CreateFileW.restype = wintypes.HANDLE
            CreateFileW.argtypes = [
                wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE
            ]

            # SetFileTime signature
            SetFileTime = ctypes.windll.kernel32.SetFileTime
            SetFileTime.restype = wintypes.BOOL
            SetFileTime.argtypes = [
                wintypes.HANDLE, ctypes.POINTER(wintypes.FILETIME),
                ctypes.POINTER(wintypes.FILETIME), ctypes.POINTER(wintypes.FILETIME)
            ]

            CloseHandle = ctypes.windll.kernel32.CloseHandle

            # Convert timestamp to filetime (100-nanosecond intervals since Jan 1, 1601)
            # EPOCH_AS_FILETIME = 116444736000000000
            # HUNDREDS_OF_NANOSECONDS = 10000000
            
            t = int((timestamp * 10000000) + 116444736000000000)
            c_creation_time = wintypes.FILETIME(t & 0xFFFFFFFF, t >> 32)

            handle = CreateFileW(path, FILE_WRITE_ATTRIBUTES, 0, None, OPEN_EXISTING, 128, None) # 128 = FILE_ATTRIBUTE_NORMAL
            
            if handle == -1: # INVALID_HANDLE_VALUE
                return

            SetFileTime(handle, byref(c_creation_time), None, None)
            CloseHandle(handle)
        except Exception as e:
            print(f"Failed to set creation time: {e}")
    else:
        # On Linux/Unix, creation time (birthtime) is hard to change reliably from Python
        pass

def to_deg(value, loc):
    """
    Converts decimal coordinates to DMS (Degrees, Minutes, Seconds) tuple for EXIF.
    """
    if value < 0:
        loc_value = loc[1]
    else:
        loc_value = loc[0]
    abs_value = abs(value)
    deg = int(abs_value)
    t1 = (deg, 1)
    min_val = (abs_value - deg) * 60
    min_int = int(min_val)
    t2 = (min_int, 1)
    sec_val = (min_val - min_int) * 60
    sec = int(sec_val * 10000)
    t3 = (sec, 10000)
    return (t1, t2, t3), loc_value

def download_photos(json_file_path, output_dir):
    """
    Downloads photos from a JSON file to a specified directory,
    renames them based on capture date, and updates EXIF metadata
    including GPS, Timezone, and Camera info.
    """

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Load Park Coordinates
    coords_map = {}
    try:
        with open('park_coordinates.json', 'r') as f:
            coords_map = json.load(f)
    except FileNotFoundError:
        print("Warning: park_coordinates.json not found. GPS tagging will be skipped.")
    except json.JSONDecodeError:
        print("Warning: Invalid JSON in park_coordinates.json.")

    try:
        with open(json_file_path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: JSON file not found at {json_file_path}")
        return
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in {json_file_path}")
        return

    encounters = data.get('guestMedia', {}).get('encounters', [])
    
    if not encounters:
        print("No encounters found in JSON.")
        return

    count = 0
    for encounter in encounters:
        orig_park = encounter.get('origPark')
        encounter_coords = coords_map.get(orig_park)
        
        media_list = encounter.get('mediaList', [])
        for media in media_list:
            # Try to get the medium resolution URI first, then thumb
            uri = media.get('mediaMedium', {}).get('uri')
            if not uri:
                uri = media.get('mediaThumb', {}).get('uri')
            
            capture_date_str = media.get('captureDate') # e.g., "2026-01-18T19:16:29Z"
            media_id = media.get('mediaId', 'unknown')

            if uri:
                # Parse capture date and format filename
                capture_dt = None
                local_dt = None
                try:
                    # Parse URL time (Zulu)
                    capture_dt = datetime.strptime(capture_date_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=ZoneInfo("UTC"))
                    
                    # Convert to Eastern Time
                    local_dt = capture_dt.astimezone(ZoneInfo("America/New_York"))
                    
                    filename_timestamp = capture_dt.strftime("%Y-%m-%d_%H-%M-%S")
                    filename = f"{filename_timestamp}_{media_id}.jpg"
                except (ValueError, TypeError, Exception) as e:
                    print(f"Warning: Could not parse date/time '{capture_date_str}' ({e}). Using ID filename.")
                    filename = f"{media_id}.jpg"

                filepath = os.path.join(output_dir, filename)
                
                print(f"Downloading {filename}...") # Shorter log
                try:
                    urllib.request.urlretrieve(uri, filepath)
                    
                    if capture_dt and local_dt:
                        # Prepare EXIF data
                        exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
                        
                        # Timestamp strings
                        datetime_original_str = local_dt.strftime("%Y:%m:%d %H:%M:%S")
                        offset_str = local_dt.strftime("%z") # +HHMM or -HHMM
                        # Insert colon for EXIF format +/-HH:MM
                        offset_str_exif = f"{offset_str[:-2]}:{offset_str[-2:]}"

                        # 0th IFD
                        exif_dict["0th"][piexif.ImageIFD.Make] = "Disney Photo Pass"
                        exif_dict["0th"][piexif.ImageIFD.Model] = "Disney Photo Pass"
                        exif_dict["0th"][piexif.ImageIFD.Software] = "Disney Photo Pass"
                        exif_dict["0th"][piexif.ImageIFD.DateTime] = datetime_original_str.encode('utf-8')

                        # Exif IFD
                        exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = datetime_original_str.encode('utf-8')
                        exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = datetime_original_str.encode('utf-8')
                        exif_dict["Exif"][piexif.ExifIFD.OffsetTime] = offset_str_exif.encode('utf-8')
                        exif_dict["Exif"][piexif.ExifIFD.OffsetTimeOriginal] = offset_str_exif.encode('utf-8')
                        exif_dict["Exif"][piexif.ExifIFD.OffsetTimeDigitized] = offset_str_exif.encode('utf-8')

                        # GPS IFD
                        if encounter_coords:
                            lat = encounter_coords.get('lat')
                            lon = encounter_coords.get('lon')
                            if lat is not None and lon is not None:
                                gps_lat, gps_lat_ref = to_deg(lat, ["N", "S"])
                                gps_lon, gps_lon_ref = to_deg(lon, ["E", "W"])
                                
                                exif_dict["GPS"][piexif.GPSIFD.GPSLatitudeRef] = gps_lat_ref.encode('utf-8')
                                exif_dict["GPS"][piexif.GPSIFD.GPSLatitude] = gps_lat
                                exif_dict["GPS"][piexif.GPSIFD.GPSLongitudeRef] = gps_lon_ref.encode('utf-8')
                                exif_dict["GPS"][piexif.GPSIFD.GPSLongitude] = gps_lon
                                
                                # GPS Timestamp (UTC)
                                gps_time = (
                                    (capture_dt.hour, 1),
                                    (capture_dt.minute, 1),
                                    (capture_dt.second, 1)
                                )
                                exif_dict["GPS"][piexif.GPSIFD.GPSTimeStamp] = gps_time
                                exif_dict["GPS"][piexif.GPSIFD.GPSDateStamp] = capture_dt.strftime("%Y:%m:%d").encode('utf-8')

                        exif_bytes = piexif.dump(exif_dict)
                        piexif.insert(exif_bytes, filepath)
                        
                        log_extras = []
                        if encounter_coords: log_extras.append(f"GPS:{orig_park}")
                        log_extras.append(f"Time:{local_dt} ({offset_str_exif})")
                        print(f"  -> Tagged {filename} [{' '.join(log_extras)}]")
                        
                        # Update File System Timestamps (Modified and Created)
                        try:
                            ts = capture_dt.timestamp()
                            # Set Access and Modified Time
                            os.utime(filepath, (ts, ts))
                            # Set Creation Time (Windows)
                            set_creation_time(filepath, ts)
                        except Exception as e:
                            print(f"  -> Warning: Could not set file timestamps: {e}")

                    count += 1
                except HTTPError as e:
                    print(f"Failed to download {uri}: {e}")
                except Exception as e:
                    print(f"An error occurred with {filename}: {e}")

    print(f"Download complete. {count} photos processed.")

if __name__ == "__main__":
    json_file = "photos.json"
    download_dir = "downloaded_photos"
    download_photos(json_file, download_dir)
