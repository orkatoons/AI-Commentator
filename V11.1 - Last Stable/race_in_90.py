import json
import pygame
import math

class Race90Visualizer:
    def __init__(self, spline_data_file):
        pygame.init()
        self.width, self.height = 1280, 720
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Race in 90 Seconds")
        
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 20)
        
        self.spline_data = self.load_spline_data(spline_data_file)
        self.drivers = self.get_unique_drivers()
        self.max_laps = self.get_max_laps()
        
        self.track_width = self.width * 0.9
        self.track_height = self.height * 0.9
        self.track_left = (self.width - self.track_width) / 2
        self.track_top = (self.height - self.track_height) / 2
        
        self.car_width = 60
        self.car_height = 25
        
        self.start_time = min(data['sessionTime'] for data in self.spline_data)
        self.end_time = max(data['sessionTime'] for data in self.spline_data)
        self.total_race_time = self.end_time - self.start_time

        self.driver_colors = self.assign_driver_colors()
        self.driver_positions = {driver: index for index, driver in enumerate(self.drivers)}
        self.overtakes = {}
        self.previous_positions = {driver: (0, 0) for driver in self.drivers}

    def load_spline_data(self, file_path):
        with open(file_path, 'r') as f:
            return json.load(f)

    def get_unique_drivers(self):
        return sorted(set(data['carIndex'] for data in self.spline_data))

    def get_max_laps(self):
        return max(data['laps'] for data in self.spline_data)

    def assign_driver_colors(self):
        colors = [
            (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), 
            (255, 0, 255), (0, 255, 255), (128, 0, 0), (0, 128, 0),
            (0, 0, 128), (128, 128, 0), (128, 0, 128), (0, 128, 128)
        ]
        return {driver: colors[i % len(colors)] for i, driver in enumerate(self.drivers)}

    def draw_track(self):
        pygame.draw.rect(self.screen, (100, 100, 100), (self.track_left, self.track_top, self.track_width, self.track_height), 2)

    def draw_car(self, car_index, x_position, y_position):
        x = self.track_left + x_position * (self.track_width - self.car_width)
        y = self.track_top + y_position * self.car_height * 1.2
        
        car_color = self.driver_colors[car_index]
        pygame.draw.rect(self.screen, car_color, (x, y, self.car_width, self.car_height))
        
        driver_abbr = f"D{car_index:02d}"
        text = self.font.render(driver_abbr, True, (255, 255, 255))
        self.screen.blit(text, (x + 5, y + 5))

        if car_index in self.overtakes:
            overtake_text = self.font.render("↑", True, (255, 255, 0))
            self.screen.blit(overtake_text, (x + self.car_width + 5, y + 5))

    def draw_session_time(self, current_time):
        minutes = int(current_time // 60000)
        seconds = int((current_time % 60000) // 1000)
        milliseconds = int(current_time % 1000)
        time_str = f"Session Time: {minutes:02d}:{seconds:02d}.{milliseconds:03d}"
        text = self.font.render(time_str, True, (255, 255, 255))
        self.screen.blit(text, (10, 10))

    def run(self):
        running = True
        frame = 0
        total_frames = 90 * 60  # 90 seconds at 60 FPS for smoother animation

        while running and frame < total_frames:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

            self.screen.fill((0, 0, 0))
            self.draw_track()

            current_time = self.start_time + (frame / total_frames) * self.total_race_time
            self.draw_session_time(current_time)
            
            car_positions = self.get_car_positions_at_time(current_time)
            if car_positions:
                self.update_positions_and_detect_overtakes(car_positions)
                for car_index, (x_pos, race_pos) in car_positions.items():
                    interp_x, interp_y = self.interpolate_position(car_index, x_pos, self.driver_positions[car_index])
                    self.draw_car(car_index, interp_x, interp_y)
                    self.previous_positions[car_index] = (x_pos, self.driver_positions[car_index])

            pygame.display.flip()
            self.clock.tick(60)  # 60 FPS for smoother animation
            frame += 1

            # Clear overtakes after a short duration
            if frame % 60 == 0:  # Clear after 1 second
                self.overtakes.clear()

        pygame.quit()

    def get_car_positions_at_time(self, target_time):
        positions = {}
        for car_index in self.drivers:
            car_data = self.get_car_data_at_time(car_index, target_time)
            if car_data:
                x_pos = car_data['splinePosition']
                race_pos = x_pos + car_data['laps']
                positions[car_index] = (x_pos, race_pos)
        return positions

    def get_car_data_at_time(self, car_index, target_time):
        car_data = [data for data in self.spline_data if data['carIndex'] == car_index and data['sessionTime'] <= target_time]
        if car_data:
            return max(car_data, key=lambda x: x['sessionTime'])
        return None

    def update_positions_and_detect_overtakes(self, car_positions):
        sorted_positions = sorted(car_positions.items(), key=lambda x: x[1][1], reverse=True)
        new_positions = {car: index for index, (car, _) in enumerate(sorted_positions)}
        
        for car, new_pos in new_positions.items():
            old_pos = self.driver_positions[car]
            if new_pos < old_pos:
                self.overtakes[car] = True
        
        self.driver_positions = new_positions

    def interpolate_position(self, car_index, new_x, new_y):
        prev_x, prev_y = self.previous_positions[car_index]
        interp_factor = 0.2  # Adjust this value to change the smoothness of the animation
        interp_x = prev_x + (new_x - prev_x) * interp_factor
        interp_y = prev_y + (new_y - prev_y) * interp_factor
        return interp_x, interp_y

if __name__ == "__main__":
    visualizer = Race90Visualizer("spline_data.json")
    visualizer.run()
