"""
Project: Herramienta basada en IA para el apoyo en la composición musical
Author: Victoria Fernández
Date: 2025-07-01
Version: 1.0.0
Description:
Este script provee la interfaz de la app que une todos los distintos pasos del proceso.
"""

import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
import subprocess
import os
import shutil

import time

import re
import sys
import wave
import contextlib
import numpy as np
from scipy.io import wavfile
import requests
from fastapi import HTTPException
import threading

TEMP_INPUT_DIR = "input_for_main_script"
API_KEY = '' # Eliminada en github

def create_scores_text():
    image_dir = "modelo/data/test/input"
    file_name = "modelo/data/test/scorestest.txt"

    image_files = []
    if os.path.exists(image_dir):
        for f in os.listdir(image_dir):
            if f.endswith('.png'):
                # "01.png" -> 1
                try:
                    num_part = int(os.path.splitext(f)[0])
                    image_files.append((num_part, f))
                except ValueError:
                    print(f"Warning: Skipping non-numeric image file in {image_dir}: {f}")
                    pass
        image_files.sort()

    num_files_found = len(image_files)

    if num_files_found == 0:
        print(f"No .png files found in '{image_dir}'. '{file_name}' will be empty.")
        with open(file_name, "w") as file:
            pass
        return

    with open(file_name, "w") as file:
        for i in range(num_files_found):
            n = i + 1
            formatted_i = f"{n:02d}" # Formats 0 as 00, 1 as 01, etc.
            file.write(f"input/{formatted_i}.png\n")
    print(f"{file_name} has been created successfully with {num_files_found} entries!")

def create_and_clean_directories():
    dirs_to_create = [
        "out",
        "out/Audio_Segments",
        "out/Spectrograms",
        "out/Reconstructed",
        "dataset-modelImages",
        "data",
        "data/gt",
        "data/input",
        "results",
        "modelo/data/test/gt",
        "modelo/data/test/input"
    ]

    # Limpiar los directorios anteriores y crear los nuevos
    for d in ["out", "dataset-modelImages", 'data', 'results']:
        if os.path.exists(d):
            print(f"Deleting existing directory: {d}")
            shutil.rmtree(d)

    for d in ["out", "dataset-modelImages"]:
        if os.path.exists(d):
            print(f"Deleting existing directory: {d}")
            shutil.rmtree(d)

    if os.path.exists(TEMP_INPUT_DIR):
        print(f"Deleting existing temporary input directory: {TEMP_INPUT_DIR}")
        shutil.rmtree(TEMP_INPUT_DIR)

    for d in dirs_to_create:
        os.makedirs(d, exist_ok=True)
        print(f"Created directory: {d}")

    os.makedirs(TEMP_INPUT_DIR, exist_ok=True)
    print(f"Created temporary input directory: {TEMP_INPUT_DIR}")

def create_request_API():
    audio_file_path = 'full_output.wav'

    if not os.path.exists(audio_file_path):
        print(f"Error: El archivo de audio no se encontró en '{audio_file_path}'")
        # raise HTTPException(status_code=404, detail=f"Audio file not found: {audio_file_path}")
        return

    with open(audio_file_path, 'rb') as audio_file:
        query_parameters = {
            'model': 'piano', # requerido por la documentación de Klang.io
            'title': 'Sugerencia', # opcional
        }

        files_to_send = {
            'file': (os.path.basename(audio_file_path), audio_file, 'audio/wav'),
        }

        data_to_send = {
            'outputs': 'pdf' # Este es el campo de texto que funcionó en curl
        }

        # print('oke oke')
        try:
            resp = requests.post(
                'https://api.klang.io/transcription',
                headers={
                    'accept': 'application/json',
                    'kl-api-key': API_KEY, 
                },
                params=query_parameters,
                files=files_to_send, 
                data=data_to_send,  
            )
            print('HA LLEGADO AQUI')
            print(f"Código de estado de la respuesta: {resp.status_code}")
            print(f"Texto completo de la respuesta: {resp.text}")

            if not resp.ok:
                print(f"¡La solicitud a la API de Klang.io falló!")
                print(f"Error de la API: {resp.text}")
                # raise HTTPException(status_code=resp.status_code, detail=f"Klango API Error: {resp.text}")
                return

            try:
                json_response = resp.json()
                print("Respuesta JSON de la API:")
                print(json_response)
                job_id = json_response.get('job_id')
                return job_id
                
            except requests.exceptions.JSONDecodeError:
                print("Error: La respuesta de la API no es un JSON válido, a pesar del código de estado exitoso.")
                print(f"Contenido completo de la respuesta: {resp.text}")
            
        except requests.exceptions.RequestException as e:
            print(f"Ocurrió un error al hacer la solicitud HTTP: {e}")
        except Exception as e:
            print(f"Ocurrió un error inesperado: {e}")

def get_result_API(job_id):

    resp = requests.get(
    'https://api.klang.io/job/' + job_id + '/pdf',
    headers={
                    'accept': 'application/json',
                    'kl-api-key': API_KEY, 
                })

    print(resp)
    if resp.status_code == 200:
        with open('test.pdf', 'wb') as file:
            file.write(resp.content)
            print(f"PDF guardado exitosamente como '{'test.pdf'}'")

def open_pdf_res():
    pdf_file_path = 'test.pdf'
    if not os.path.exists(pdf_file_path):
        print(f"Error: El archivo PDF no se encontró en '{pdf_file_path}'")
        return

    try:
        if sys.platform.startswith('win32'): # Windows
            os.startfile(pdf_file_path)
            print(f"PDF abierto en Windows: '{pdf_file_path}'")
        elif sys.platform.startswith('linux'):  # Linux
            subprocess.call(('xdg-open', pdf_file_path))
            print(f"PDF abierto en Linux: '{pdf_file_path}'")
        else:
            print(f"No se pudo determinar el sistema operativo para abrir el PDF. Intenta abrirlo manualmente: '{pdf_file_path}'")
    except FileNotFoundError:
        print(f"Error: No se encontró la aplicación predeterminada para abrir PDFs en tu sistema.")
    except Exception as e:
        print(f"Ocurrió un error al intentar abrir el PDF: {e}")

status_text = "Cargando"
animation_running = True

def execute_commands_and_show_view():
    global animation_running, status_text

    global file_path
    if not file_path:
        messagebox.showwarning("Ningún archivo seleccionado", "Por favor, selecciona un archivo.")
        return

    root.update_idletasks() # Mostrar "cargando" en el GUI
    
    try:
        ######### PASO 0 || Partitura a audio
        #---------------------
        print(f"Seleccionado archivo: {file_path}")

        result = subprocess.run(
            ["musescore/musescore_audio.sh", file_path],
            check=True,
            capture_output=True,
            text=True
        )
        print("musescore file to audio successful")

        print("main.py stdout:\n", result.stdout)
        if result.stderr:
            print("main.py stderr:\n", result.stderr)

        file_name = os.path.basename(file_path)
        print(file_name)
        archivo_audio = file_name.replace("mscz", "wav")
        print(archivo_audio)

        ######### PASO 1 || Carpetas
        #---------------------
        create_and_clean_directories()

        ######### PASO 2 || Audio to spec
        #---------------------
        # Copiar el audio de input a un dir temportal
        destination_path = os.path.join(TEMP_INPUT_DIR, archivo_audio)
        final_archivo_path = os.path.join('musescore/out', archivo_audio)

        print(final_archivo_path)
        shutil.copy(final_archivo_path, destination_path)
        print(f"Archivo '{archivo_audio}' copiado a '{destination_path}'")

        print("Ejecutando main... audio to images")
        result = subprocess.run(
            ["python3", "main.py", "--mode", "audio_to_image", "--input_audio_dir", TEMP_INPUT_DIR],
            check=True,
            capture_output=True,
            text=True
        )

        print("main.py stdout:\n", result.stdout)
        if result.stderr:
            print("main.py stderr:\n", result.stderr)

        ######### PASO 3 || Preparar carpeta 'data' para el modelo
        #---------------------
        source_dir = "dataset-modelImages"
        gt_dest_dir = "modelo/data/test/gt"
        input_dest_dir = "modelo/data/test/input"

        # Copiar las imagenes preparadas
        if os.path.exists(source_dir) and os.listdir(source_dir):
            # 'data/gt'
            for item_name in os.listdir(source_dir):
                s = os.path.join(source_dir, item_name)
                d = os.path.join(gt_dest_dir, item_name)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)
                print(f"Copiado {item_name} a {gt_dest_dir}")

            # 'data/input'
            for item_name in os.listdir(source_dir):
                s = os.path.join(source_dir, item_name)
                d = os.path.join(input_dest_dir, item_name)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)
                print(f"Copiado {item_name} a {input_dest_dir}")
        else:
            print(f"Advertencia: La carpeta '{source_dir}' no existe o está vacía. No se copiará nada a 'data/gt' y 'data/input'.")

        ######### PASO 4 || Preparar el archivo scores.text
        create_scores_text()

        status_text = "Evaluando con el modelo"
        root.update_idletasks()

        ######### PASO 5 || Evaluar con el modelo
        # # python3 eval_diffusion.py --config "scores.yml" --resume "ckpts/Scores_ddpm.pth.tar" --test_set "scores"

        print("Ejecutando evaluacion")
        result = subprocess.run(
            ["python3", "modelo/eval_diffusion.py", "--config", "scores.yml", "--resume", "modelo/ckpts/Scores_ddpm.pth.tar", "--test_set", "scores"],
            check=True,
            capture_output=True,
            text=True
        )

        status_text = "Procesando resultados"
        root.update_idletasks()

        ######## PASO 6 || Coger los resultados
        # ---------------------
        source_dir = "results/images/Scores/scores"
        dest_dir = "results"

        # Copiar los espectrogramas resultantes 
        if os.path.exists(source_dir) and os.listdir(source_dir):
            for item_name in os.listdir(source_dir):
                s = os.path.join(source_dir, item_name)
                d = os.path.join(dest_dir, item_name)
                if os.path.isdir(s):
                    shutil.copytree(s, d, dirs_exist_ok=True)
                else:
                    shutil.copy2(s, d)
                print(f"Copiado {item_name} a {dest_dir}")

        else:
            print(f"Advertencia: La carpeta '{source_dir}' no existe o está vacía. No se copiará nada a 'data/gt' y 'data/input'.")

        ######### PASO 7 || Transformar los spectrograms resultantes a audio
        #---------------------
        print("Ejecutando main... spectrograms to audios")
        result = subprocess.run(
            ["python3", "main.py", "--mode", "image_to_audio", "--input_spec_dir", "results"],
            check=True,
            capture_output=True,
            text=True
        )

        print("main.py stdout:\n", result.stdout)
        if result.stderr:
            print("main.py stderr:\n", result.stderr)

        ######### PASO 8 || Unir los audios en uno completo
        #---------------------
        ordered_files = get_ordered_wav_files('out/Reconstructed')
        concatenate_wav_files(ordered_files, 'full_output.wav')

        status_text = "Preparando la partitura"
        root.update_idletasks()

        ######### PASO 9 || Transcribir con Kanglio
        #---------------------
        job_id = create_request_API()
        
        get_result_API(job_id)

        ######### PASO 10 || Abrir el pdf
        #---------------------
        open_pdf_res()

        status_label.config(text="Completado")

        status_label.config(fg="green")  # Cambia el color a verde

        status_text = "Completado!!"

        root.update_idletasks()


    except subprocess.CalledProcessError as e:
        messagebox.showerror("Error en comando", f"Ha ocurrido un error en la ejecución: {e.stderr}")
        status_label.config(text="Error!")
        return
    except Exception as e:
        messagebox.showerror("Error", f"Ha ocurrido un error inesperado: {e}")
        status_label.config(text="Error!")
        return


def select_file():
    global file_path
    file_path = filedialog.askopenfilename(filetypes=[("MuseScore files", "*.mscz")])
    if file_path:
        file_label.config(text=f"Seleccionado: {file_path.split('/')[-1]}")
        status_label.config(text="", fg="green")

def get_ordered_wav_files(folder_path):
    files = os.listdir(folder_path)
    print(files)
    wav_files = [f for f in files if f.endswith('_output_reconstructed.wav')]
    def extract_index(f):
        match = re.search(r"\[\'(\d+)\'\]", f)
        return int(match.group(1)) if match else -1

    wav_files.sort(key=extract_index)
    print(wav_files)
    return [os.path.join(folder_path, f) for f in wav_files]

def concatenate_wav_files(file_paths, output_path):
    sample_rate = None
    all_audio = []

    for path in file_paths:
        rate, data = wavfile.read(path)
        if sample_rate is None:
            sample_rate = rate
        elif rate != sample_rate:
            raise ValueError(f"Inconsistent sample rate in file {path}")
        all_audio.append(data)

    combined = np.concatenate(all_audio)
    wavfile.write(output_path, sample_rate, combined)
    print(f"✅ Combined audio saved to {output_path}")

def loading_animation():
    global status_text, animation_running

    loading_suffix = ["", ".", "..", "..."]
    i = 0
    while animation_running:
        status_label.config(text=status_text + loading_suffix[i % 4], fg="blue")
        root.update_idletasks()
        time.sleep(0.4)
        i += 1

def run_with_loading():
    global animation_running, status_text

    animation_running = True
    status_text = "Cargando los datos"
    anim_thread = threading.Thread(target=loading_animation)
    anim_thread.start()

    # Lógica principal
    execute_commands_and_show_view()

    # Detener animación
    animation_running = False
    anim_thread.join()

    root.after(0, root.destroy)

def show_view_window():
    view_window = tk.Toplevel(root)
    view_window.title("Ver resultados")
    view_window.geometry("300x100")
    tk.Label(view_window, text="Completado!").pack(pady=20)
    tk.Button(view_window, text="Cerrar", command=view_window.destroy).pack()


if __name__ == "__main__":
    root = tk.Tk()
    root.title("MusAI")

    root.geometry("600x220")
    root.configure(bg="#f2f2f2")

    font_main = ("Segoe UI", 11)

    file_path = "" # variable to save the file path selected

    # FIle selection
    file_frame = tk.Frame(root, bg="#f2f2f2", pady=10)
    file_frame.pack()

    tk.Label(file_frame, text="Selecciona un archivo:", font=font_main, bg="#f2f2f2").pack(side=tk.LEFT, padx=5)
    file_label = tk.Label(file_frame, text="Ningún archivo seleccionado", fg="#007bff", font=font_main, bg="#f2f2f2")
    file_label.pack(side=tk.LEFT, padx=5)
    select_button = tk.Button(file_frame, text="Buscar", font=font_main, command=select_file, bg="#e0e0e0", relief="flat")
    select_button.pack(side=tk.LEFT, padx=5)

    next_button = tk.Button(root, text="Siguiente", command=lambda: threading.Thread(target=run_with_loading).start(),
                        font=("Segoe UI", 12, "bold"), bg="#007bff", fg="white", padx=10, pady=6)

    next_button.pack(pady=15)

    # Label de estado
    status_label = tk.Label(root, text="", font=("Segoe UI", 13, "bold"), bg="#f2f2f2")
    status_label.pack(pady=10)

    root.mainloop()