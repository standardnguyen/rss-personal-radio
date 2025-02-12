# %%
import os
import requests
import shutil
from elevenlabs.client import ElevenLabs, VoiceSettings
from elevenlabs import play
import datetime
from vocoder import vocode_audio
from update_trello_card_audio import update_trello_card_audio

# %%
client = ElevenLabs()

# %%
# Get the current date and time
now = datetime.datetime.now()

# Format the date as "Saturday, December 21, 2025"
formatted_date = now.strftime("%A, %B %d, %Y")

print(formatted_date)

dummy_text = "Good morning, Standard! Today is " + formatted_date


# %%
# Define the directory for saving the generated MP3 (if needed)
personal_daily_intro_dir = os.path.join("temp", "personal_daily_intro")
os.makedirs(personal_daily_intro_dir, exist_ok=True)

# Set your dummy text directly in the code

# Convert the text to speech using the ElevenLabs API
audio = client.text_to_speech.convert(
    text=dummy_text,
    voice_id="15ykVVhNtZjeRtlW8QZC",
    model_id="eleven_multilingual_v2",
    output_format="mp3_44100_128",
    voice_settings=VoiceSettings(
        stability=0.5,
        similarity_boost=0.75,
        style=0.4,
        use_speaker_boost=True
    )
)

# Create the output MP3 file name
output_mp3_path = os.path.join(personal_daily_intro_dir, "eleven_personal_intro.mp3")

# Write the audio stream to the MP3 file
with open(output_mp3_path, "wb") as mp3_file:
    for chunk in audio:
        mp3_file.write(chunk)

print(f"Saved MP3 to {output_mp3_path}")


# %%
vocoded_output_path = os.path.join(personal_daily_intro_dir, "eleven_personal_intro.wav")


vocode_audio(output_mp3_path, vocoded_output_path)

# %%
update_trello_card_audio("Daily Wakeup Intro", vocoded_output_path)


