import sys
import os
from PyQt5.QtCore import QThread, pyqtSignal
from datetime import datetime, timedelta
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from accapi.client import AccClient

class DataCollector(QThread):
    output_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.client = AccClient()
        self.running = False
        self.cars = {}
        self.session_info = {}
        self.last_update_time = 0
        self.update_interval = 4
        self.previous_positions = {}
        self.race_started = False
        self.session_time_ms = 0
        self.race_start_time = None
        self.current_accidents = {}
        self.initialization_complete = False
        self.output_file = None
        self.cars_in_pits = set()
        self.last_position_display = 0
        self.final_lap_phase = False
        self.finished_cars = set()
        self.leader_finished = False
        self.leader_car_index = None
        self.total_laps = None
        self.start_line_crossed = set()
        self.qualifying_reported = False
        self.spline_data = []  # New: Store spline data for each update cycle

    def run(self):
        self.running = True
        self.setup_client()
        self.start_client()

        self.output_signal.emit("Initializing data collection...")

        while not self.initialization_complete and self.running:
            self.msleep(500)

        if self.initialization_complete:
            self.setup_output_file()
            self.output_signal.emit("Data collection initialized. Starting race monitoring...")

        while self.running:
            self.msleep(self.update_interval * 1000)
            if self.race_started:
                self.update_race_data()

        # New: Save spline data to a JSON file when the race ends
        self.save_spline_data()

    def stop(self):
        self.running = False
        self.stop_client()
        self.output_signal.emit("Data collection stopped.")

    def setup_client(self):
        self.client.onRealtimeUpdate.subscribe(self.on_realtime_update)
        self.client.onRealtimeCarUpdate.subscribe(self.on_realtime_car_update)
        self.client.onEntryListCarUpdate.subscribe(self.on_entry_list_car_update)
        self.client.onBroadcastingEvent.subscribe(self.on_broadcasting_event)

    def start_client(self):
        self.client.start(
            url="localhost",
            port=9000,
            password="asd",
            commandPassword="",
            displayName="Python ACC Data Collector",
            updateIntervalMs=500
        )

    def stop_client(self):
        if self.client.isAlive:
            self.client.stop()

    def on_realtime_update(self, event):
        update = event.content
        self.session_info = {
            "sessionType": update.sessionType,
            "sessionPhase": update.sessionPhase,
        }
        self.session_time_ms = update.sessionTimeMs

        if not self.initialization_complete:
            if update.sessionType == "Race" and update.sessionPhase != "Pre Session":
                self.initialization_complete = True
                if self.session_time_ms == 0:
                    self.output_signal.emit("Waiting for the race to start.")
                else:
                    self.output_signal.emit(f"Joined ongoing race. Current session time: {self.format_session_time(self.session_time_ms)}")

        if not self.race_started and update.sessionType == "Race" and update.sessionPhase == "Session":
            self.race_started = True
            self.race_start_time = datetime.now() - timedelta(milliseconds=self.session_time_ms)
            self.log_event("The Race Begins!")

        if self.race_started and not self.final_lap_phase:
            elapsed_time = self.session_time_ms / 1000
            if elapsed_time >= 240 and (elapsed_time - self.last_position_display) >= 240:
                self.display_positions()
                self.last_position_display = elapsed_time

        if update.sessionPhase == "Session Over" and not self.final_lap_phase:
            self.final_lap_phase = True
            self.log_event("Leader is on final lap")

        if self.final_lap_phase and not self.leader_finished:
            self.check_race_finish()

    def on_realtime_car_update(self, event):
        car = event.content
        if car.carIndex not in self.cars:
            self.cars[car.carIndex] = {'carIndex': car.carIndex, 'previous_spline': 0, 'laps': 0}
        
        current_car = self.cars[car.carIndex]
        current_car.update({
            'position': car.position,
            'driverName': current_car.get('driverName', f'Car {car.carIndex}'),
            'laps': car.laps,
            'splinePosition': car.splinePosition,
            'location': car.location,
        })

        # New: Store spline data for each update cycle
        self.spline_data.append({
            'sessionTime': self.session_time_ms,
            'carIndex': car.carIndex,
            'splinePosition': car.splinePosition,
            'laps': car.laps,
        })

        # Pit entry/exit logging
        if car.carIndex not in self.finished_cars:
            if car.location in ["Pitlane", "Pit Entry"] and car.carIndex not in self.cars_in_pits:
                self.cars_in_pits.add(car.carIndex)
                driver_name = current_car.get('driverName', f"Car {car.carIndex}")
                self.log_event(f"{driver_name} has entered the pits.")
            elif car.location not in ["Pitlane", "Pit Entry"] and car.carIndex in self.cars_in_pits:
                self.cars_in_pits.remove(car.carIndex)
                driver_name = current_car.get('driverName', f"Car {car.carIndex}")
                self.log_event(f"{driver_name} has exited the pits.")

    def on_entry_list_car_update(self, event):
        car = event.content
        if car.carIndex not in self.cars:
            self.cars[car.carIndex] = {'carIndex': car.carIndex, 'previous_spline': 0, 'laps': 0}
        if car.drivers:
            driver = car.drivers[0]
            self.cars[car.carIndex]['driverName'] = f"{driver.firstName} {driver.lastName}"
            self.cars[car.carIndex]['driverSurname'] = driver.lastName
            self.cars[car.carIndex]['nationality'] = driver.nationality

    def on_broadcasting_event(self, event):
        event_content = event.content
        event_type = event_content.type
        if event_type == "Session Over":
            self.log_event("Leader is on final lap")
            self.final_lap_phase = True
        elif event_type == "Accident":
            accident_time = self.format_session_time(self.session_time_ms)
            car_index = event_content.carIndex

            if car_index not in self.finished_cars:
                try:
                    driver = self.cars[car_index].get('driverName', f'Car {car_index}')
                except KeyError:
                    driver = f'Unknown Car {car_index}'

                if accident_time not in self.current_accidents:
                    self.current_accidents[accident_time] = []

                self.current_accidents[accident_time].append(driver)

    def check_race_finish(self):
        sorted_cars = self.get_sorted_cars()
        leader = sorted_cars[0]
        if leader['splinePosition'] > 0.99 and not self.leader_finished:
            self.leader_finished = True
            self.total_laps = leader['laps']
            self.log_event(f"Checkered flag! {leader['driverName']} takes the win!")
            self.report_race_results(sorted_cars)

    def report_race_results(self, sorted_cars):
        for position, car in enumerate(sorted_cars, start=1):
            driver_name = car.get('driverName', f"Car {car['carIndex']}")
            self.log_event(f"{driver_name} has finished in position {position}.")
            self.finished_cars.add(car['carIndex'])

    def get_sorted_cars(self):
        return sorted(self.cars.values(), key=lambda x: (-x.get('laps', 0), -x.get('splinePosition', 0)))

    def get_qualifying_order(self):
        return sorted(self.cars.values(), key=lambda x: x.get('position', float('inf')))

    def report_qualifying_results(self):
        qualifying_order = self.get_qualifying_order()
        result_string = "Qualifying results: " + ", ".join(
            f"(P{car.get('position', i+1)}) {car.get('driverName', f'Car {car['carIndex']}')} ({car.get('nationality', 'Unknown')})"
            for i, car in enumerate(qualifying_order)
        )
        self.log_event(result_string)

    def display_positions(self):
        sorted_cars = self.get_sorted_cars()
        positions = []
        for position, car in enumerate(sorted_cars, start=1):
            if car['carIndex'] not in self.finished_cars:
                driver_name = car.get('driverName', f"Car {car['carIndex']}")
                positions.append(f"(P{position}) {driver_name}")
        position_string = "Current positions: " + ", ".join(positions)
        self.log_event(position_string)

    def update_race_data(self):
        sorted_cars = self.get_sorted_cars()

        current_positions = {car['carIndex']: i+1 for i, car in enumerate(sorted_cars) if car['carIndex'] not in self.cars_in_pits and car['carIndex'] not in self.finished_cars}
        overtakes = self.detect_overtakes(current_positions) if self.session_time_ms >= 15000 else []

        self.previous_positions = current_positions

        for overtake in overtakes:
            self.log_event(overtake)

        accidents = self.current_accidents
        self.current_accidents = {}  # Clear the current accidents after processing

        for accident_time, drivers in accidents.items():
            drivers_str = ", ".join(drivers)
            self.log_event(f"Accident involving: {drivers_str}")

    def detect_overtakes(self, current_positions):
        overtakes = []
        if not self.previous_positions or not self.race_started:
            return overtakes

        for car_index, current_pos in current_positions.items():
            if car_index in self.previous_positions and car_index not in self.finished_cars:
                previous_pos = self.previous_positions[car_index]
                if current_pos < previous_pos:
                    try:
                        overtaker = self.cars[car_index].get('driverName', f"Car {car_index}")
                    except KeyError:
                        overtaker = f"Unknown Car {car_index}"
                    for other_index, other_pos in current_positions.items():
                        if other_index != car_index and other_index not in self.finished_cars and other_pos == current_pos + 1 and self.previous_positions.get(other_index, 0) < previous_pos:
                            try:
                                overtaken = self.cars[other_index].get('driverName', f"Car {other_index}")
                            except KeyError:
                                overtaken = f"Unknown Car {other_index}"
                            overtakes.append(f"Overtake! {overtaker} overtook {overtaken} for position {current_pos}.")
        return overtakes

    def format_session_time(self, milliseconds):
        seconds = int(milliseconds // 1000)
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"

    def setup_output_file(self):
        if not os.path.exists("Race Data"):
            os.makedirs("Race Data")

        start_time = datetime.now()
        filename = start_time.strftime("%Y-%m-%d_%H-%M-%S") + ".txt"
        self.output_file = os.path.join("Race Data", filename)

        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write(f"Race data collection started at: {start_time}\n\n")

    def log_event(self, event):
        formatted_time = self.format_session_time(self.session_time_ms)
        log_message = f"{formatted_time} - {event}"

        self.output_signal.emit(log_message)

        if self.output_file:
            try:
                with open(self.output_file, 'a', encoding='utf-8') as f:
                    f.write(log_message + '\n')
            except UnicodeEncodeError:
                with open(self.output_file, 'a', encoding='utf-8', errors='replace') as f:
                    f.write(log_message + '\n')

    def save_spline_data(self):
        spline_file = os.path.join("Race Data", "spline_data.json")
        with open(spline_file, 'w') as f:
            json.dump(self.spline_data, f)
        self.output_signal.emit(f"Spline data saved to {spline_file}")                    

    def get_output_file_path(self):
        return self.output_file
