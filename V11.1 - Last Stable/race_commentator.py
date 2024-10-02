import os
import re
import time
from PyQt5.QtCore import QThread, pyqtSignal
import anthropic

class RaceCommentator(QThread):
    output_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)

    def __init__(self, input_path, api_key):
        super().__init__()
        self.input_path = input_path
        self.output_path = None
        self.client = anthropic.Anthropic(api_key=api_key)
        self.system_prompt = self.load_prompt("race_commentator_prompt.txt")

    def run(self):
        self.output_signal.emit("Starting race commentary generation...")
        self.progress_signal.emit(0)

        try:
            messages = []
            race_history = ""
            total_events = self.count_events()
            processed_events = 0

            with open(self.input_path, 'r') as input_file:
                self.output_path = self.create_output_file()

                for line in input_file:
                    match = re.match(r'(\d{2}:\d{2}:\d{2}) - (.+)', line.strip())
                    if match:
                        timecode, event_data = match.groups()
                        commentary = self.get_ai_commentary(messages, event_data, race_history)

                        self.write_commentary(timecode, commentary)
                        race_history += f"{timecode} - {event_data}\n"

                        processed_events += 1
                        progress = int((processed_events / total_events) * 100)
                        self.progress_signal.emit(progress)

            self.output_signal.emit(f"Commentary generation complete. Output saved to {self.output_path}")
            self.progress_signal.emit(100)

        except Exception as e:
            self.output_signal.emit(f"An error occurred: {str(e)}")

    def count_events(self):
        with open(self.input_path, 'r') as file:
            return sum(1 for line in file if re.match(r'\d{2}:\d{2}:\d{2} - ', line))

    def load_prompt(self, filename):
        try:
            with open(filename, 'r') as file:
                return file.read()
        except FileNotFoundError:
            return f"Error: {filename} not found. Please create this file with the desired prompt."

    def get_ai_commentary(self, messages, event_data, race_history):
        context = f"Race history:\n{race_history}\n\nCurrent event: {event_data}"
        messages.append({"role": "user", "content": context})

        response = self.client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=500,
            temperature=0.9,
            system=self.system_prompt,
            messages=messages
        )

        commentary = response.content[0].text
        messages.append({"role": "assistant", "content": commentary})
        return commentary

    def create_output_file(self):
        base_name = os.path.basename(self.input_path)
        file_name, file_extension = os.path.splitext(base_name)
        new_file_name = f"{file_name}_commentary{file_extension}"

        original_dir = os.path.dirname(self.input_path)
        return os.path.join(original_dir, new_file_name)

    def write_commentary(self, timecode, commentary):
        with open(self.output_path, 'a', encoding='utf-8') as f:
            f.write(f"{timecode} - {commentary}\n")
        self.output_signal.emit(f"{timecode} - {commentary}")

    def get_output_path(self):
        return self.output_path
