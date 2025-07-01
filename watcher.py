import os
import json
import time
import subprocess

TRIGGER_FILE = "/tmp/tfg_trigger.json"

def main():
    print("Esperando trigger desde MuseScore...")

    last_timestamp = None

    while True:
        if os.path.exists(TRIGGER_FILE):
            with open(TRIGGER_FILE) as f:
                try:
                    data = json.load(f)
                    timestamp = data.get("timestamp")
                    if timestamp != last_timestamp:
                        last_timestamp = timestamp
                        print(f"Trigger detectado: {timestamp}")
                        subprocess.Popen(["/bin/python3", "/home/vic/Desktop/tfg/app.py"])
                except Exception as e:
                    print("Error leyendo trigger:", e)

        time.sleep(1)

if __name__ == "__main__":
    main()
