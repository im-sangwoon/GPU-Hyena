import os
import time
import requests
import pynvml
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 60))
MEMORY_THRESHOLD_MB = int(os.getenv("MEMORY_THRESHOLD_MB", 1000))

def get_gpu_status():
    pynvml.nvmlInit()
    device_count = pynvml.nvmlDeviceGetCount()
    free_gpus = []

    print(f"[{datetime.now()}] Checking {device_count} GPUs...")

    for i in range(device_count):
        handle = pynvml.nvmlDeviceGetHandleByIndex(i)
        name = pynvml.nvmlDeviceGetName(handle)
        if isinstance(name, bytes):
            name = name.decode('utf-8')
            
        mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        util_rates = pynvml.nvmlDeviceGetUtilizationRates(handle)
        
        used_mem_mb = mem_info.used / 1024 / 1024
        total_mem_mb = mem_info.total / 1024 / 1024
        gpu_util = util_rates.gpu
        
        print(f"  GPU {i} ({name}): Memory {used_mem_mb:.0f}/{total_mem_mb:.0f} MB, Util {gpu_util}%")

        # Condition for "Free": Used memory < Threshold AND GPU Utilization < 5%
        # You can adjust the utilization threshold as needed.
        if used_mem_mb < MEMORY_THRESHOLD_MB and gpu_util < 5:
            free_gpus.append({
                "index": i,
                "name": name,
                "memory_used": used_mem_mb,
                "memory_total": total_mem_mb,
                "utilization": gpu_util
            })

    pynvml.nvmlShutdown()
    return free_gpus

def send_discord_notification(free_gpus):
    if not WEBHOOK_URL:
        print("Error: DISCORD_WEBHOOK_URL not found in .env")
        return

    if not free_gpus:
        return

    description = ""
    for gpu in free_gpus:
        description += f"**GPU {gpu['index']}**: {gpu['name']}\n"
        description += f"Memory: {gpu['memory_used']:.0f}MB / {gpu['memory_total']:.0f}MB\n"
        description += f"Utilization: {gpu['utilization']}%\n\n"

    data = {
        "content": "🚨 **GPU Available!** 🚨",
        "embeds": [
            {
                "title": "Free GPUs Detected",
                "description": description,
                "color": 5763719  # Greenish color
            }
        ]
    }

    try:
        response = requests.post(WEBHOOK_URL, json=data)
        response.raise_for_status()
        print(f"[{datetime.now()}] Notification sent!")
    except requests.exceptions.RequestException as e:
        print(f"Error sending notification: {e}")

def main():
    print("Starting GPU Hyena...")
    print(f"Threshold: < {MEMORY_THRESHOLD_MB} MB Memory Used")
    
    # To prevent spamming, we can track notified GPUs or just sleep.
    # For simplicity, we'll just sleep. 
    # A more advanced version might wait until the GPU is taken before notifying again about the same GPU,
    # or use a longer cooldown.
    
    last_notified_time = 0
    COOLDOWN = 300 # 5 minutes cooldown between notifications to avoid spamming if no one takes it immediately

    while True:
        try:
            free_gpus = get_gpu_status()
            
            if free_gpus:
                current_time = time.time()
                if current_time - last_notified_time > COOLDOWN:
                    send_discord_notification(free_gpus)
                    last_notified_time = current_time
                else:
                    print(f"[{datetime.now()}] Free GPUs detected, but in cooldown.")
            else:
                print(f"[{datetime.now()}] No free GPUs.")
                
        except Exception as e:
            print(f"Error: {e}")
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
