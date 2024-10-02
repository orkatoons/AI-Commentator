import os
import re
import requests
from PyQt5.QtCore import QThread, pyqtSignal

class VoiceGenerator(QThread):
    output_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)

    def __init__(self, input_path, api_key):
        super().__init__()
        self.input_path = input_path
        self.output_dir = "audio output"
        self.chunk_size = 1024
        self.xi_api_key = api_key
        self.voice_id = "Mw9TampTt4PGYMa0FYBO"  # Default voice ID
        self.tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream"

    def run(self):
        self.output_signal.emit("Starting voice commentary generation...")
        self.progress_signal.emit(0)

        try:
            os.makedirs(self.output_dir, exist_ok=True)

            total_lines = self.count_lines()
            processed_lines = 0

            with open(self.input_path, 'r') as file:
                for line in file:
                    match = re.match(r'(\d{2}:\d{2}:\d{2}) - (.+)', line.strip())
                    if match:
                        time_code, text = match.groups()
                        self.generate_audio(text, time_code)

                        processed_lines += 1
                        progress = int((processed_lines / total_lines) * 100)
                        self.progress_signal.emit(progress)

            self.output_signal.emit("Voice generation complete!")
            self.progress_signal.emit(100)

        except Exception as e:
            self.output_signal.emit(f"An error occurred: {str(e)}")

    def count_lines(self):
        with open(self.input_path, 'r') as file:
            return sum(1 for line in file if re.match(r'\d{2}:\d{2}:\d{2} - ', line))

    def generate_audio(self, text, time_code):
        # Remove line breaks and page breaks from the text
        text = re.sub(r'\s+', ' ', text).strip()

        headers = {
            "Accept": "application/json",
            "xi-api-key": self.xi_api_key
        }
        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.7,
                "similarity_boost": 0.8,
                "style": 0.4,
                "use_speaker_boost": True
            }
        }

        response = requests.post(self.tts_url, headers=headers, json=data, stream=True)

        if response.ok:
            output_path = os.path.join(self.output_dir, f"Commentary_{time_code.replace(':', '')}.mp3")

            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    f.write(chunk)

            self.output_signal.emit(f"Audio saved: {output_path}")
        else:
            self.output_signal.emit(f"Error generating audio for time {time_code}: {response.text}")

    def get_output_dir(self):
        return os.path.abspath(self.output_dir)

    def set_voice(self, voice_id):
        self.voice_id = voice_id
        self.tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream"
