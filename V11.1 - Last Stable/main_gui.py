import sys
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QComboBox, QTextEdit, 
                             QFileDialog, QProgressBar, QLineEdit, QFormLayout, QMessageBox)
from PyQt5.QtCore import Qt, QSettings
from data_collector_ACC import DataCollector as DataCollectorACC
from data_collector_AMS2 import DataCollector as DataCollectorAMS2
from data_collector_AC import DataCollector as DataCollectorAC
from data_filterer import DataFilterer
from race_commentator import RaceCommentator
from voice_generator import VoiceGenerator
from race_in_90 import Race90Visualizer

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Bad AI Commentary")
        self.setGeometry(100, 100, 800, 600)

        self.settings = QSettings("BadAICommentary", "SimRacingCommentator")

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.tab_widget = QTabWidget()
        self.layout.addWidget(self.tab_widget)

        self.setup_tab = QWidget()
        self.race_visualization_tab = QWidget()
        self.highlight_reel_tab = QWidget()
        self.commentary_tab = QWidget()
        self.voice_tab = QWidget()
        self.settings_tab = QWidget()

        self.tab_widget.addTab(self.setup_tab, "Setup")
        self.tab_widget.addTab(self.race_visualization_tab, "Race Visualization")
        self.tab_widget.addTab(self.highlight_reel_tab, "Highlight Reel Creation")
        self.tab_widget.addTab(self.commentary_tab, "Commentary Generation")
        self.tab_widget.addTab(self.voice_tab, "Voice Generation")
        self.tab_widget.addTab(self.settings_tab, "Settings")

        self.setup_setup_tab()
        self.setup_race_visualization_tab()
        self.setup_highlight_reel_tab()
        self.setup_commentary_tab()
        self.setup_voice_tab()
        self.setup_settings_tab()

        self.status_bar = self.statusBar()
        self.progress_bar = QProgressBar()
        self.status_bar.addPermanentWidget(self.progress_bar)

    def setup_setup_tab(self):
        layout = QVBoxLayout(self.setup_tab)

        sim_label = QLabel("Select your sim:")
        self.sim_combo = QComboBox()
        self.sim_combo.addItems(["Assetto Corsa Competizione", "Assetto Corsa", "Automobilista 2"])

        self.start_stop_button = QPushButton("Start")
        self.start_stop_button.clicked.connect(self.toggle_data_collection)

        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)

        layout.addWidget(sim_label)
        layout.addWidget(self.sim_combo)
        layout.addWidget(self.start_stop_button)
        layout.addWidget(self.console_output)

    def setup_race_visualization_tab(self):
        layout = QVBoxLayout(self.race_visualization_tab)

        data_path_label = QLabel("Enter the path to your spline data file:")
        self.visualization_data_path_input = QLineEdit()
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_visualization_data_file)

        visualize_button = QPushButton("Visualize Race")
        visualize_button.clicked.connect(self.visualize_race)

        self.visualization_output = QTextEdit()
        self.visualization_output.setReadOnly(True)

        layout.addWidget(data_path_label)
        layout.addWidget(self.visualization_data_path_input)
        layout.addWidget(browse_button)
        layout.addWidget(visualize_button)
        layout.addWidget(self.visualization_output)

    def setup_highlight_reel_tab(self):
        layout = QVBoxLayout(self.highlight_reel_tab)

        prompt_label = QLabel("AI Prompt:")
        self.ai_prompt = QTextEdit()
        self.ai_prompt.setPlainText(self.load_prompt("highlight_reel_prompt.txt"))

        data_path_label = QLabel("Enter the path to your race data file:")
        self.data_path_input = QLineEdit()
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_data_file)

        filter_button = QPushButton("Filter Data")
        filter_button.clicked.connect(self.filter_data)

        self.filter_output = QTextEdit()
        self.filter_output.setReadOnly(True)

        save_highlights_button = QPushButton("Save Highlights")
        save_highlights_button.clicked.connect(self.save_highlights)

        layout.addWidget(prompt_label)
        layout.addWidget(self.ai_prompt)
        layout.addWidget(data_path_label)
        layout.addWidget(self.data_path_input)
        layout.addWidget(browse_button)
        layout.addWidget(filter_button)
        layout.addWidget(self.filter_output)
        layout.addWidget(save_highlights_button)

    def setup_commentary_tab(self):
        layout = QVBoxLayout(self.commentary_tab)

        input_label = QLabel("Input file:")
        self.commentary_input = QLineEdit()
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_commentary_input)

        generate_button = QPushButton("Generate Commentary")
        generate_button.clicked.connect(self.generate_commentary)

        self.commentary_output = QTextEdit()
        self.commentary_output.setReadOnly(True)

        layout.addWidget(input_label)
        layout.addWidget(self.commentary_input)
        layout.addWidget(browse_button)
        layout.addWidget(generate_button)
        layout.addWidget(self.commentary_output)

    def setup_voice_tab(self):
        layout = QVBoxLayout(self.voice_tab)

        input_label = QLabel("Input file:")
        self.voice_input = QLineEdit()
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_voice_input)

        generate_button = QPushButton("Generate Voice Commentary")
        generate_button.clicked.connect(self.generate_voice)

        self.voice_output = QTextEdit()
        self.voice_output.setReadOnly(True)

        layout.addWidget(input_label)
        layout.addWidget(self.voice_input)
        layout.addWidget(browse_button)
        layout.addWidget(generate_button)
        layout.addWidget(self.voice_output)

    def setup_settings_tab(self):
        layout = QFormLayout(self.settings_tab)

        self.claude_api_key_input = QLineEdit()
        self.claude_api_key_input.setEchoMode(QLineEdit.Password)
        self.claude_api_key_input.setText(self.settings.value("claude_api_key", ""))

        self.eleven_labs_api_key_input = QLineEdit()
        self.eleven_labs_api_key_input.setEchoMode(QLineEdit.Password)
        self.eleven_labs_api_key_input.setText(self.settings.value("eleven_labs_api_key", ""))

        layout.addRow("Claude API Key:", self.claude_api_key_input)
        layout.addRow("ElevenLabs API Key:", self.eleven_labs_api_key_input)

        save_button = QPushButton("Save Settings")
        save_button.clicked.connect(self.save_settings)
        layout.addRow(save_button)

    def toggle_data_collection(self):
        if self.start_stop_button.text() == "Start":
            self.start_data_collection()
        else:
            self.stop_data_collection()

    def start_data_collection(self):
        sim = self.sim_combo.currentText()
        if sim == "Assetto Corsa Competizione":
            self.data_collector = DataCollectorACC()
        elif sim == "Assetto Corsa":
            self.data_collector = DataCollectorAC()
        else:
            self.data_collector = DataCollectorAMS2()

        self.data_collector.output_signal.connect(self.update_console)
        self.data_collector.progress_signal.connect(self.update_progress_bar)
        self.data_collector.start()
        self.start_stop_button.setText("Stop")

    def stop_data_collection(self):
        if hasattr(self, 'data_collector'):
            self.data_collector.stop()
            self.update_console("Data collection stopped.")
        self.start_stop_button.setText("Start")

    def update_console(self, text):
        self.console_output.append(text)

    def browse_data_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Select Race Data File", "", "Text Files (*.txt)")
        if file_name:
            self.data_path_input.setText(file_name)

    def browse_visualization_data_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Select Spline Data File", "", "JSON Files (*.json)")
        if file_name:
            self.visualization_data_path_input.setText(file_name)

    def visualize_race(self):
        spline_data_file = self.visualization_data_path_input.text()
        if not spline_data_file:
            QMessageBox.warning(self, "Input Missing", "Please select a spline data file.")
            return

        try:
            visualizer = Race90Visualizer(spline_data_file)
            visualizer.run()
            self.visualization_output.append("Race visualization completed successfully.")
        except Exception as e:
            self.visualization_output.append(f"Error during race visualization: {str(e)}")

    def filter_data(self):
        input_path = self.data_path_input.text()
        claude_api_key = self.get_claude_api_key()
        if not claude_api_key:
            QMessageBox.warning(self, "API Key Missing", "Please enter your Claude API key in the Settings tab.")
            return
        self.data_filterer = DataFilterer(input_path, claude_api_key)
        self.data_filterer.output_signal.connect(self.update_filter_output)
        self.data_filterer.progress_signal.connect(self.update_progress_bar)
        self.data_filterer.start()

    def update_filter_output(self, text):
        self.filter_output.append(text)

    def save_highlights(self):
        highlights = self.filter_output.toPlainText()
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Highlights", "", "Text Files (*.txt)")
        if file_name:
            with open(file_name, 'w') as f:
                f.write(highlights)
            self.update_console(f"Highlights saved to {file_name}")

    def browse_commentary_input(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Select Input File", "", "Text Files (*.txt)")
        if file_name:
            self.commentary_input.setText(file_name)

    def generate_commentary(self):
        input_path = self.commentary_input.text()
        if not input_path:
            input_path = self.data_filterer.get_output_path() if hasattr(self, 'data_filterer') else None
        
        if not input_path:
            QMessageBox.warning(self, "Input Missing", "Please select an input file.")
            return

        claude_api_key = self.get_claude_api_key()
        if not claude_api_key:
            QMessageBox.warning(self, "API Key Missing", "Please enter your Claude API key in the Settings tab.")
            return

        self.race_commentator = RaceCommentator(input_path, claude_api_key)
        self.race_commentator.output_signal.connect(self.update_commentary_output)
        self.race_commentator.progress_signal.connect(self.update_progress_bar)
        self.race_commentator.start()

    def update_commentary_output(self, text):
        self.commentary_output.append(text)

    def browse_voice_input(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Select Input File", "", "Text Files (*.txt)")
        if file_name:
            self.voice_input.setText(file_name)

    def generate_voice(self):
        input_path = self.voice_input.text()
        if not input_path:
            input_path = self.race_commentator.get_output_path() if hasattr(self, 'race_commentator') else None
        
        if not input_path:
            QMessageBox.warning(self, "Input Missing", "Please select an input file.")
            return

        eleven_labs_api_key = self.get_eleven_labs_api_key()
        if not eleven_labs_api_key:
            QMessageBox.warning(self, "API Key Missing", "Please enter your ElevenLabs API key in the Settings tab.")
            return

        self.voice_generator = VoiceGenerator(input_path, eleven_labs_api_key)
        self.voice_generator.output_signal.connect(self.update_voice_output)
        self.voice_generator.progress_signal.connect(self.update_progress_bar)
        self.voice_generator.start()

    def update_voice_output(self, text):
        self.voice_output.append(text)

    def update_progress_bar(self, value):
        self.progress_bar.setValue(value)

    def save_settings(self):
        claude_api_key = self.claude_api_key_input.text()
        eleven_labs_api_key = self.eleven_labs_api_key_input.text()

        self.settings.setValue("claude_api_key", claude_api_key)
        self.settings.setValue("eleven_labs_api_key", eleven_labs_api_key)

        QMessageBox.information(self, "Settings Saved", "Your API keys have been saved successfully.")

    def get_claude_api_key(self):
        return self.settings.value("claude_api_key", "")

    def get_eleven_labs_api_key(self):
        return self.settings.value("eleven_labs_api_key", "")

    def load_prompt(self, filename):
        try:
            with open(filename, 'r') as file:
                return file.read()
        except FileNotFoundError:
            return f"Error: {filename} not found. Please create this file with the desired prompt."

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
