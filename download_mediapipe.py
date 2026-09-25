# download_mediapipe.py
import os
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_DIR = os.path.join(BASE_DIR, 'face', 'static', 'face', 'mediapipe')
WASM_DIR = os.path.join(TARGET_DIR, 'wasm')

os.makedirs(WASM_DIR, exist_ok=True)

CDN_BASE = 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14'
GOOGLE_STORAGE = 'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1'

files = {
    os.path.join(TARGET_DIR, 'vision_bundle.mjs'): 
        f'{CDN_BASE}/vision_bundle.mjs',
    
    os.path.join(TARGET_DIR, 'face_landmarker.task'): 
        f'{GOOGLE_STORAGE}/face_landmarker.task',
    
    os.path.join(WASM_DIR, 'vision_wasm_internal.js'): 
        f'{CDN_BASE}/wasm/vision_wasm_internal.js',
    
    os.path.join(WASM_DIR, 'vision_wasm_internal.wasm'): 
        f'{CDN_BASE}/wasm/vision_wasm_internal.wasm',
    
    os.path.join(WASM_DIR, 'vision_wasm_nosimd_internal.js'): 
        f'{CDN_BASE}/wasm/vision_wasm_nosimd_internal.js',
    
    os.path.join(WASM_DIR, 'vision_wasm_nosimd_internal.wasm'): 
        f'{CDN_BASE}/wasm/vision_wasm_nosimd_internal.wasm',
}

print('شروع دانلود فایل‌های MediaPipe...')
for dest, url in files.items():
    print(f'Downloading: {os.path.basename(dest)} ...')
    try:
        urllib.request.urlretrieve(url, dest)
        print(f'  ✅ Saved: {dest}')
    except Exception as e:
        print(f'  ❌ ERROR: {e}')

print('\n✅ تمام فایل‌ها دانلود شدند.')