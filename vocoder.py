"""
audio_processor.py

A module to process audio files with optional effects (pitch shift, ring modulation,
bandpass filtering, flanger, and phaser). The main function `process_audio(input_file, output_file)`
loads an audio file, applies the enabled effects, and writes the result to a new file.
"""

import librosa
import numpy as np
import soundfile as sf
from pedalboard import Pedalboard, Phaser, Chorus
import scipy.signal as sps
from scipy.signal import butter, lfilter

# --- TOGGLE THESE FLAGS AND PARAMETERS AS NEEDED ---
DO_PITCH_SHIFT = False
PITCH_SHIFT_STEPS = -3  # e.g. -3 semitones to lower pitch

DO_RING_MOD = False
RING_MOD_FREQ = 400  # Frequency for ring modulation in Hz

DO_BANDPASS = False
BANDPASS_LOW = 300   # Lower bound frequency in Hz
BANDPASS_HIGH = 5000  # Upper bound frequency in Hz

DO_FLANGER = True             # Set to False to skip flanger
FLANGER_RATE = 1              # LFO rate in Hz (e.g., between 0.1 Hz and 5 Hz)
FLANGER_DEPTH = 0.8           # Depth of modulation (0 to 1)
FLANGER_CENTRE_DELAY_MS = 3.0 # Centre delay in ms (lower values yield a flanger-like effect)
FLANGER_FEEDBACK = 0.5        # Amount of feedback (0 to ~0.9)
FLANGER_MIX = 0.2             # Wet/dry mix (0 = all dry, 1 = all wet)

DO_PHASER = True   # Toggle phaser effect
PHASER_RATE = 1.5  # Rate of modulation in Hz
PHASER_DEPTH = 0.7 # Depth of modulation (0 to 1)
PHASER_MIX = 0.5   # Wet/dry mix (0 = all dry, 1 = all wet)


def bandpass_filter(data, lowcut, highcut, fs, order=4):
    """
    Apply a simple Butterworth bandpass filter.

    Parameters:
        data (np.ndarray): Input audio signal.
        lowcut (float): Lower cutoff frequency in Hz.
        highcut (float): Upper cutoff frequency in Hz.
        fs (int): Sampling rate.
        order (int): Order of the filter (default is 4).

    Returns:
        np.ndarray: Filtered audio signal.
    """
    nyquist = 0.5 * fs
    low = lowcut / nyquist
    high = highcut / nyquist
    b, a = butter(order, [low, high], btype='band')
    return lfilter(b, a, data)


def apply_convolution_reverb(signal, ir):
    """
    Convolve the input signal with an impulse response (IR).

    Parameters:
        signal (np.ndarray): Input audio signal.
        ir (np.ndarray): Impulse response signal.

    Returns:
        np.ndarray: Reverberated audio signal.
    """
    return sps.fftconvolve(signal, ir, mode='full')


def vocode_audio(input_file, output_file):
    """
    Process the audio file at 'input_file' and write the processed audio to 'output_file'.

    The function applies a series of effects (pitch shift, ring modulation, bandpass filter,
    flanger, phaser) depending on the toggled flags.

    Parameters:
        input_file (str): Path to the input audio file.
        output_file (str): Path where the processed audio will be saved.
    """
    # Load the input audio file (supports MP3, WAV, OGG, FLAC, etc.)
    y, sr = librosa.load(input_file, sr=None)
    y_current = y.copy()
    print(f"Loaded {len(y)} samples at {sr} Hz from '{input_file}'.")

    # --- Pitch Shift ---
    if DO_PITCH_SHIFT:
        print(f"Applying pitch shift: {PITCH_SHIFT_STEPS} semitones...")
        y_current = librosa.effects.pitch_shift(
            y=y_current,
            sr=sr,
            n_steps=PITCH_SHIFT_STEPS,
            bins_per_octave=12,
            res_type='kaiser_best'
        )
    else:
        print("Skipping pitch shift.")

    # --- Ring Modulation ---
    if DO_RING_MOD:
        print(f"Applying ring modulation at {RING_MOD_FREQ} Hz...")
        duration = len(y_current) / sr
        t = np.linspace(0, duration, len(y_current), endpoint=False)
        carrier = np.sin(2.0 * np.pi * RING_MOD_FREQ * t)
        y_current = y_current * carrier
    else:
        print("Skipping ring modulation.")

    # --- Bandpass Filter ---
    if DO_BANDPASS:
        print(f"Applying bandpass filter from {BANDPASS_LOW} Hz to {BANDPASS_HIGH} Hz...")
        y_current = bandpass_filter(y_current, BANDPASS_LOW, BANDPASS_HIGH, sr)
    else:
        print("Skipping bandpass filter.")

    # --- Flanger Effect ---
    if DO_FLANGER:
        print(f"Applying flanger: rate={FLANGER_RATE} Hz, depth={FLANGER_DEPTH}, "
              f"centre_delay={FLANGER_CENTRE_DELAY_MS} ms, feedback={FLANGER_FEEDBACK}, mix={FLANGER_MIX}")
        # Convert mono audio to 2D array (channels x samples) as required by Pedalboard
        y_2d = np.expand_dims(y_current, axis=0)
        flanger_plugin = Chorus(
            rate_hz=FLANGER_RATE,
            depth=FLANGER_DEPTH,
            centre_delay_ms=FLANGER_CENTRE_DELAY_MS,
            feedback=FLANGER_FEEDBACK,
            mix=FLANGER_MIX
        )
        board = Pedalboard([flanger_plugin])
        processed = board(y_2d, sample_rate=sr)
        y_current = np.squeeze(processed, axis=0)
        print("Flanger applied.")
    else:
        print("Skipping flanger.")

    # --- Phaser Effect ---
    if DO_PHASER:
        print(f"Applying phaser: rate={PHASER_RATE} Hz, depth={PHASER_DEPTH}, mix={PHASER_MIX}...")
        y_2d = np.expand_dims(y_current, axis=0)
        board = Pedalboard([
            Phaser(rate_hz=PHASER_RATE, depth=PHASER_DEPTH, mix=PHASER_MIX),
        ])
        processed = board(y_2d, sample_rate=sr)
        y_current = np.squeeze(processed, axis=0)
        print("Phaser applied.")
    else:
        print("Skipping phaser.")

    # Write the processed audio to the output file
    sf.write(output_file, y_current, sr)
    print(f"Done! Processed audio written to '{output_file}'.")


# Optional: allow the module to be run as a script using a command-line interface.
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Process an audio file with various effects.")
    parser.add_argument("input", help="Path to the input audio file.")
    parser.add_argument("output", help="Path to save the processed audio file.")
    args = parser.parse_args()

    process_audio(args.input, args.output)
