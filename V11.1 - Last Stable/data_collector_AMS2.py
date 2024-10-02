import ctypes
import mmap
import time
from datetime import datetime
import os
from shared_memory_struct import SharedMemory
from PyQt5.QtCore import QThread, pyqtSignal

class DataCollector(QThread):
    output_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.shared_memory_file = "$pcars2$"
        self.memory_size = ctypes.sizeof(SharedMemory)
        self.output_file = None
        self.previous_distances = {}
        self.previous_times = {}
        self.accident_logged = {}
        self.last_game_time = None
        self.last_pit_latch = {}
        self.previous_positions = {}
        self.running = False
        self.file_handle = None
        self.last_overtake_update = 0

    def setup_shared_memory(self):
        """Sets up access to the shared memory file."""
        try:
            self.file_handle = mmap.mmap(-1, self.memory_size, self.shared_memory_file, access=mmap.ACCESS_READ)
            self.output_signal.emit("Shared memory setup complete.")
        except Exception as e:
            self.output_signal.emit(f"Error setting up shared memory: {e}")

    def read_shared_memory(self):
        """Reads data from shared memory."""
        try:
            data = SharedMemory()
            self.file_handle.seek(0)
            ctypes.memmove(ctypes.addressof(data), self.file_handle.read(ctypes.sizeof(data)), ctypes.sizeof(data))
            return data
        except Exception as e:
            self.output_signal.emit(f"Error reading shared memory: {e}")
            return None

    def setup_output_file(self):
        """Sets up the output file for logging race data."""
        try:
            directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Race Data")
            os.makedirs(directory, exist_ok=True)
            start_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            self.output_file = os.path.join(directory, f"{start_time}.txt")
            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.write(f"Race data collection started at: {start_time}\n\n")
            self.output_signal.emit(f"Output file setup complete: {self.output_file}")
        except Exception as e:
            self.output_signal.emit(f"Error setting up output file: {e}")

    def calculate_speed(self, current_time, total_distance, participant_index):
        """Calculates the speed in km/h of a participant."""
        prev_time = self.previous_times.get(participant_index)
        prev_distance = self.previous_distances.get(participant_index)
        
        if prev_time is not None and prev_distance is not None:
            time_diff = current_time - prev_time
            distance_diff = total_distance - prev_distance

            if time_diff > 0 and distance_diff > 0:
                speed_kph = (distance_diff / time_diff) * 3.6  # Convert m/s to km/h
                
                if 0 <= speed_kph <= 300:  # Filter unrealistic speeds
                    return speed_kph
        return None

    def log_event(self, event, pit_mode=None):
        """Logs an event to the output file and emits it as a signal."""
        try:
            if pit_mode is not None:
                event += f" (Pit Mode: {pit_mode})"
            self.output_signal.emit(f"Logging event: {event}")
            with open(self.output_file, 'a', encoding='utf-8') as f:
                f.write(event + "\n")
        except Exception as e:
            self.output_signal.emit(f"Error logging event: {e}")

    def process_participant_data(self, data):
        """Processes the data for each participant."""
        game_time = data.mCurrentTime

        # Skip processing if the game is paused
        if self.last_game_time == game_time:
            return

        current_time = time.time()
        update_overtakes = current_time - self.last_overtake_update >= 2

        for i in range(data.mNumParticipants):
            participant_data = data.mParticipantInfo[i]
            if participant_data.mIsActive:
                current_lap = participant_data.mCurrentLap
                current_lap_distance = participant_data.mCurrentLapDistance
                lap_length = data.mTrackLength
                total_distance = ((1 - current_lap) * lap_length) + current_lap_distance
                participant_name = participant_data.mName.decode('utf-8').strip('\x00')
                speed_kph = self.calculate_speed(game_time, total_distance, i)

                if speed_kph is not None:
                    pit_mode = data.mPitModes[i]

                    # Pit latch logic
                    if pit_mode == 1:  # Entering pits
                        self.last_pit_latch[i] = game_time
                    elif pit_mode == 3:  # Exiting pits
                        self.last_pit_latch[i] = None

                    # Record accident if not latched in pits
                    if self.last_pit_latch.get(i) is None:
                        if speed_kph < 20 and current_lap > 1 and game_time >= 3:
                            if not self.accident_logged.get(i, False):
                                accident_event = f"{self.format_time(game_time)} - Accident involving: {participant_name}"
                                self.log_event(accident_event)
                                self.accident_logged[i] = True

                    # Reset accident logged flag when speed exceeds 100 km/h
                    if speed_kph > 100:
                        self.accident_logged[i] = False

                    # Detect overtakes (only update every 2 seconds)
                    if update_overtakes:
                        current_position = participant_data.mRacePosition
                        previous_position = self.previous_positions.get(i)

                        if previous_position and previous_position != current_position:
                            for j in range(data.mNumParticipants):
                                if j != i and self.previous_positions.get(j) == current_position:
                                    overtaken_name = data.mParticipantInfo[j].mName.decode('utf-8').strip('\x00')
                                    overtake_event = f"{self.format_time(game_time)} - Overtake! {participant_name} overtook {overtaken_name} for position {current_position}"
                                    self.log_event(overtake_event)

                        # Update previous position
                        self.previous_positions[i] = current_position

                # Update previous distance and time
                self.previous_distances[i] = total_distance
                self.previous_times[i] = game_time

        if update_overtakes:
            self.last_overtake_update = current_time

        self.last_game_time = game_time  # Update the last game time after processing

    def format_time(self, game_time):
        """Formats the game time into HH:MM:SS."""
        total_seconds = int(game_time)
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    def run(self):
        """Main loop for reading shared memory and processing data."""
        self.output_signal.emit("Starting data collection...")
        self.running = True
        self.setup_shared_memory()
        self.setup_output_file()

        try:
            while self.running:
                data = self.read_shared_memory()
                if data:
                    self.process_participant_data(data)
                time.sleep(0.2)
        except Exception as e:
            self.output_signal.emit(f"Error in data collection: {e}")
        finally:
            if self.file_handle:
                self.file_handle.close()
            self.output_signal.emit("Data collection stopped.")

    def stop(self):
        """Stops the data collection process."""
        self.running = False

def main():
    collector = DataCollector()
    collector.run()

if __name__ == "__main__":
    main()
