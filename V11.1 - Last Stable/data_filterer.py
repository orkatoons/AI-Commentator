import os
import requests
from PyQt5.QtCore import QThread, pyqtSignal
from datetime import datetime, timedelta
import anthropic

class DataFilterer(QThread):
    output_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)

    def __init__(self, input_path, api_key):
        super().__init__()
        self.input_path = input_path
        self.output_path = None
        self.client = anthropic.Anthropic(api_key=api_key)
        self.prompt = self.load_prompt("data_filterer_prompt.txt")

    def run(self):
        self.output_signal.emit("Starting data filtering...")
        self.progress_signal.emit(0)

        try:
            race_data = self.get_file_content(self.input_path)
            self.progress_signal.emit(10)

            filtered_content = self.filter_race_data(race_data)
            self.progress_signal.emit(50)

            processed_events = self.calculate_commentary_words(filtered_content.split('\n'))
            self.progress_signal.emit(75)

            self.output_path = self.create_filtered_file(processed_events)
            self.progress_signal.emit(100)

            self.output_signal.emit(f"Filtered data saved to {self.output_path}")
        except Exception as e:
            self.output_signal.emit(f"An error occurred: {str(e)}")

    def get_file_content(self, path):
        if path.startswith(('http://', 'https://')):
            response = requests.get(path)
            response.raise_for_status()
            return response.text
        else:
            with open(path, 'r', encoding='utf-8') as file:
                return file.read()

    def load_prompt(self, filename):
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                return file.read()
        except FileNotFoundError:
            return f"Error: {filename} not found. Please create this file with the desired prompt."

    def filter_race_data(self, race_data):
        message = self.client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=4000,
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": f"{self.prompt}\n\nHere is the race data to filter:\n\n<race_data>\n{race_data}\n</race_data>"
                }
            ]
        )

        filtered_content = message.content[0].text if isinstance(message.content, list) else message.content
        return filtered_content

    def calculate_commentary_words(self, events):
        processed_events = []
        for i, event in enumerate(events):
            parts = event.split(' - ', 1)
            if len(parts) != 2:
                continue  # Skip this event if it doesn't have the expected format
            
            time_str, description = parts
            try:
                current_time = datetime.strptime(time_str, '%H:%M:%S')
            except ValueError:
                continue  # Skip this event if the time format is incorrect

            if i < len(events) - 1:
                next_parts = events[i+1].split(' - ', 1)
                if len(next_parts) != 2:
                    continue  # Skip to the next event if the next one doesn't have the expected format
                
                next_time_str = next_parts[0]
                try:
                    next_time = datetime.strptime(next_time_str, '%H:%M:%S')
                    time_diff = (next_time - current_time).total_seconds()
                    words = int(time_diff * 2)
                except ValueError:
                    words = 0  # Default to 0 if there's an issue with the next time
            else:
                words = 0  # Last event doesn't have a word count

            if words > 0:
                processed_events.append(f"{event} Commentate in {words} words.")
            else:
                processed_events.append(event)

        return processed_events

    def create_filtered_file(self, filtered_content):
        base_name = os.path.basename(self.input_path)
        file_name, file_extension = os.path.splitext(base_name)
        new_file_name = f"{file_name}_filtered{file_extension}"

        original_dir = os.path.dirname(self.input_path)
        new_file_path = os.path.join(original_dir, new_file_name)

        with open(new_file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(filtered_content))

        return new_file_path

    def get_output_path(self):
        return self.output_path
