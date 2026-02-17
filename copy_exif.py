import os
import shutil
import piexif
from PIL import Image
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
            
            t = int((timestamp * 10000000) + 116444736000000000)
            c_creation_time = wintypes.FILETIME(t & 0xFFFFFFFF, t >> 32)

            handle = CreateFileW(path, FILE_WRITE_ATTRIBUTES, 0, None, OPEN_EXISTING, 128, None)
            
            if handle == -1:
                return

            SetFileTime(handle, byref(c_creation_time), None, None)
            CloseHandle(handle)
        except Exception as e:
            print(f"Failed to set creation time: {e}")

def copy_exif_data(source_dir, target_dir):
    """
    Copies EXIF data from source images to target images if filenames match.
    """
    if not os.path.exists(source_dir):
        print(f"Source directory not found: {source_dir}")
        return
    
    if not os.path.exists(target_dir):
        print(f"Target directory not found: {target_dir}")
        return

    # Get list of files in target directory
    target_files = [f for f in os.listdir(target_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
    
    print(f"Found {len(target_files)} images in {target_dir} to process.")
    
    count = 0
    for filename in target_files:
        target_path = os.path.join(target_dir, filename)
        source_path = os.path.join(source_dir, filename)
        
        # Try to find exact match first
        if not os.path.exists(source_path):
            # Try to find match without "cleaned_" prefix if it exists? 
            # Or maybe the cleaned files have same name. Assuming same name for now based on user request.
            # If the user's cleaned files have a suffix/prefix, we might need to adjust logic.
            # Let's check if there's a file with same name
            pass

        if os.path.exists(source_path):
            try:
                # Read EXIF from source
                # distinct handling for different formats if needed, but piexif works with jpg/webp mostly
                # Pillow is safer for general metadata reading
                
                src_img = Image.open(source_path)
                if 'exif' in src_img.info:
                    exif_bytes = src_img.info['exif']
                    
                    # Write to target
                    # For PNG, piexif might not work directly, need to check format
                    if target_path.lower().endswith(('.jpg', '.jpeg')):
                        # Reload target image to avoid file lock issues if any, though piexif.insert takes path
                        piexif.insert(exif_bytes, target_path)
                        print(f"Copied EXIF for {filename}")
                        count += 1
                    elif target_path.lower().endswith('.png'):
                         # PNG metadata handling is different, Pillow can save it but piexif is mainly for JPEG
                         # We can try to save it using Pillow. Opening target again.
                         tgt_img = Image.open(target_path)
                         tgt_img.save(target_path, exif=exif_bytes)
                         print(f"Copied EXIF for {filename} (PNG re-saved)")
                         count += 1
                    elif target_path.lower().endswith('.webp'):
                        tgt_img = Image.open(target_path)
                        tgt_img.save(target_path, exif=exif_bytes)
                        print(f"Copied EXIF for {filename} (WebP re-saved)")
                        count += 1
                    
                    # Copy File Timestamps (Creation and Modified)
                    try:
                        # Get source timestamps
                        src_stat = os.stat(source_path)
                        created_time = src_stat.st_ctime
                        modified_time = src_stat.st_mtime
                        
                        # Set Modified/Access Time
                        os.utime(target_path, (src_stat.st_atime, modified_time))
                        
                        # Set Creation Time (Windows specific mostly)
                        set_creation_time(target_path, created_time)
                        
                        # print(f"  -> Timestamps copied for {filename}")
                    except Exception as e:
                        print(f"  -> Warning: Could not copy timestamps for {filename}: {e}")

                else:
                    print(f"No EXIF in source for {filename}")
            except Exception as e:
                print(f"Failed to copy EXIF for {filename}: {e}")
        else:
            print(f"Source file not found for {filename}")

    print(f"Finished. Updated {count} images.")

if __name__ == "__main__":
    # Define directories
    # Assuming 'downloaded_photos' is source and 'cleaned' is target based on ls output
    SOURCE_DIR = "downloaded_photos"
    TARGET_DIR = "cleaned"
    
    copy_exif_data(SOURCE_DIR, TARGET_DIR)
