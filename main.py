# python3 main.py --mode audio_to_image
# python3 main.py --mode image_to_audio

import argparse
import os
import numpy as np
from PIL import Image
import audio_utilities
from pylab import cm
import librosa
import soundfile as sf
import shutil

def split_audio(file_path, output_dir, segment_length=1, sample_rate=44100):
    
    print(f"Splitting {file_path} into {segment_length}-second segments")
    
    y, sr = librosa.load(file_path, sr=sample_rate)
    
    samples_per_segment = segment_length * sr
    
    base_name = os.path.basename(file_path)
    file_name = os.path.splitext(base_name)[0]
    
    segment_paths = []
    total_segments = int(np.ceil(len(y) / samples_per_segment))
    
    for i in range(total_segments):
        start = i * samples_per_segment
        end = min(start + samples_per_segment, len(y))
        
        # If the last segment is too short, pad it with zeros
        segment = y[start:end]
        if len(segment) < samples_per_segment:
            segment = np.pad(segment, (0, samples_per_segment - len(segment)))
        
        segment_path = os.path.join(output_dir, f"{file_name}_segment_{i+1:02d}.wav")
        sf.write(segment_path, segment, sr)
        segment_paths.append(segment_path)
    
    return segment_paths

def audio_to_spectrogram(audio_path, output_image_path, fft_size=2048):
    print(f"Converting {audio_path} to spectrogram")
    
    input_signal = audio_utilities.get_signal(audio_path)
    
    hopsamp = fft_size // 8
    
    stft_full = audio_utilities.stft_for_reconstruction(input_signal, fft_size, hopsamp)
    
    stft_mag = abs(stft_full)**2.0
    
    scale = 1.0 / np.amax(stft_mag)
    stft_mag *= scale
    
    transformed_data = stft_mag.T ** 0.125
    scaled_data = np.clip(transformed_data * 255, 0, 255).astype(np.uint8)
    
    image = Image.fromarray(scaled_data)
    image.save(output_image_path)
    
    return output_image_path, scale

#2046
def spectrogram_to_audio(image_path, output_audio_path, scale_factor, fft_size=2078, iterations=300, sample_rate=44100): # fft_size=2048 y cambiado audio utilities line 293
    print(f"Converting {image_path} back to audio")

    loaded_image = Image.open(image_path).convert('L')
    
    loaded_array = np.array(loaded_image)
    
    loaded_array_normalized = loaded_array.astype(np.float32) / 255.0
    
    reversed_transformed_data = loaded_array_normalized ** 8
    stft_mag = reversed_transformed_data.T
    
    stft_modified_scaled = stft_mag / scale_factor
    stft_modified_scaled = stft_modified_scaled**0.5
    
    hopsamp = fft_size // 8
    
    x_reconstruct = audio_utilities.reconstruct_signal_griffin_lim(stft_modified_scaled, fft_size, hopsamp, iterations)
    
    max_sample = np.max(abs(x_reconstruct))
    if max_sample > 1.0:
        x_reconstruct = x_reconstruct / max_sample
    
    sf.write(output_audio_path, x_reconstruct, sample_rate)
    
    return output_audio_path

def process_audio_to_images(input_directory, output_segment_dir, output_spectrogram_dir, dataset_dir):
    scale_factors = {}
    dataset_counter = 1
    
    for root, _, files in os.walk(input_directory):
        files.sort()

        current_segment_dir = output_segment_dir
        current_spectrogram_dir = output_spectrogram_dir
        current_dataset_dir = dataset_dir
        current_dataset_counter = dataset_counter
        
        for file in files:
            if file.endswith(('.wav', '.mp3')):
                audio_path = os.path.join(root, file)
                
                segment_paths = split_audio(audio_path, current_segment_dir, segment_length=1)
                
                for segment_path in segment_paths:
                    segment_name = os.path.basename(segment_path)
                    base_name = os.path.splitext(segment_name)[0]
                    
                    spectrogram_path = os.path.join(current_spectrogram_dir, f"{base_name}.png")
                    spectrogram_path, scale = audio_to_spectrogram(segment_path, spectrogram_path)
                    scale_factors[spectrogram_path] = scale
                    
                    formatted_counter = f"{current_dataset_counter:02d}"
                    dataset_path = os.path.join(current_dataset_dir, f"{formatted_counter}.png")
                    shutil.copy(spectrogram_path, dataset_path)
                    current_dataset_counter += 1
                        
    return scale_factors

def process_images_to_audio(spectrogram_dir, output_dir, scale_factors):

    for file in os.listdir(spectrogram_dir):
        if file.endswith('.png'):
            image_path = os.path.join(spectrogram_dir, file)
            base_name = os.path.splitext(file)[0]
            
            scale = scale_factors.get(image_path, 1.0)
            print(f"Scale factor for {image_path}: {scale}")
            
            output_audio_path = os.path.join(output_dir, f"{base_name}_reconstructed.wav")
            spectrogram_to_audio(image_path, output_audio_path, scale)

def main():
    parser = argparse.ArgumentParser(description='Audio processing and transformation tool')
    parser.add_argument('--mode', type=str, choices=['audio_to_image', 'image_to_audio', 'both'], 
                        default='both', help='Processing mode')
    parser.add_argument('--fft_size', default=2048, type=int, help='FFT size')
    parser.add_argument('--sample_rate', default=44100, type=int, help='Sample rate in Hz')
    parser.add_argument('--iterations', default=300, type=int, help='Number of Griffin-Lim iterations')
    parser.add_argument('--segment_length', default=2, type=int, help='Length of audio segments in seconds')
    parser.add_argument('--input_audio_dir', type=str,
                        help='Directory containing the audio file(s) to process in audio_to_image mode.')
    
    parser.add_argument('--input_spec_dir', type=str,
                        help='Directory containing the spec file(s) to process in image_to_audio mode.')
    
    args = parser.parse_args()
    
    output_segment_dir = 'out/Audio_Segments'
    output_spectrogram_dir = 'out/Spectrograms'
    output_reconstructed_dir = 'out/Reconstructed'
    dataset_dir = 'dataset-modelImages'
    
    scale_factors = {}
    
    if args.mode in ['audio_to_image']:
        print(args.input_audio_dir)
        if args.input_audio_dir and os.path.exists(args.input_audio_dir):
            print(f"Audio escogido de input: {args.input_audio_dir}")
            new_scales = process_audio_to_images(
                args.input_audio_dir,
                output_segment_dir,
                output_spectrogram_dir,
                dataset_dir
            )
            scale_factors.update(new_scales)
        else:
            print(f"Warning: No valid --input_audio_dir provided or directory does not exist for audio_to_image mode.")
    
    if args.mode in ['image_to_audio']:
        if args.input_spec_dir and os.path.exists(args.input_spec_dir):
            print(f"Audio escogido de input: {args.input_spec_dir}")
            process_images_to_audio(
                args.input_spec_dir, 
                output_reconstructed_dir, 
                scale_factors
            )

if __name__ == '__main__':
    main()
