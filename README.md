# Disney PhotoPass Downloader & Tagger

Tools to download your Disney PhotoPass memories, tag them with accurate GPS & timestamps, and restore metadata to processed (watermark-removed) images.

## Features

- **Download**: Fetches original resolution photos from your MyDisney account data.
- **Smart Tagging**: Automatically adds EXIF metadata:
  - **GPS**: Maps park locations (e.g., `BOARDWALK`, `POLY`) to precise coordinates.
  - **Timestamps**: Converts "Zulu" (UTC) time to local Eastern Time for `DateTimeOriginal` and sets correct time zones (e.g., `-04:00`/`-05:00`).
  - **File Attributes**: Sets file `Creation` and `Modified` dates on your computer to match the actual photo capture time.
- **Metadata Restoration**: Copies all metadata from downloaded originals to your cleaned/edited versions.

## Setup

1.  Requires Python 3.9+
2.  Install dependencies using `pipenv`:
    ```bash
    pipenv install
    ```
    This will install `piexif`, `Pillow`, and `tzdata` from the Pipfile.

## Usage Guide

### 1. Get Your Photos Data

1.  Log in to your account on [Disney World PhotoPass](https://disneyworld.disney.go.com/photopass/).
2.  Open the **Network** tab in your browser's Developer Tools (F12).
3.  Refresh the page or scroll to load photos.
4.  Look for a request typically named `all-media` or similar:
    ```
    https://disneyworld.disney.go.com/photopass-api/all-media?sortAscending=false&pagenum=1&pagesize=100&friendsAndFamily=false
    ```
5.  Copy the entire **Response** JSON content.
6.  Paste it into a file named `photos.json` in this directory.

*Note: You can see an example of the expected structure in `photos_example.json`.*

### 2. Configure Locations

Check `park_coordinates.json` and ensure it maps the `origPark` locations found in your `photos.json` to GPS coordinates.

Example `park_coordinates.json`:
```json
{
    "BOARDWALK": {
        "lat": 28.366466,
        "lon": -81.555981
    },
    "POLY": {
        "lat": 28.405309,
        "lon": -81.585231
    }
}
```

### 3. Download & Tag

Run the downloader script:
```bash
python download_photos.py
```
This will:
- Download all photos to the `downloaded_photos/` folder.
- Rename files based on their capture timestamp (e.g., `2026-01-18_14-14-20_ID.jpg`).
- Embed specific GPS coordinates and timestamps into the image metadata.
- Set the file created/modified dates on your disk.

### 4. Restore Metadata (Optional)

If you process your downloaded photos (e.g., to remove watermarks) and save them to a new folder (e.g., `cleaned/`), you can re-apply the correct metadata from the originals.

Run the copy script:
```bash
python copy_exif.py
```
*Note: Ensure your source folder (`downloaded_photos`) matches the variable `SOURCE_DIR` and your target folder (`cleaned`) matches `TARGET_DIR` inside the script if you changed them.*
