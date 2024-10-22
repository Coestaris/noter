#!/usr/bin/env python3

#
# @file main.py
# @date 18-10-2024
# @author Maxim Kurylko <vk_vm@ukr.net>
#

__description__ = ""
__version__ = "0.1.0"

import logging
import os
from typing import Optional, Tuple, List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTabWidget, QWidget, \
    QCheckBox, QLabel, QHBoxLayout, QSpinBox, QPushButton, QSizePolicy, \
    QGridLayout, QComboBox, QGroupBox, QRadioButton, QApplication

from music import Note, Scale, Clef
from smufl import SMUFLFont
from stave import Stave


def setup_logging(args):
    class Fore:
        GREEN = "\x1b[32m"
        CYAN = "\x1b[36m"
        RED = "\x1b[31m"
        YELLOW = "\x1b[33m"
        RESET = "\x1b[39m"

    def get_format_string(colored: bool, details: bool) -> str:
        green = Fore.GREEN if colored else ""
        cyan = Fore.CYAN if colored else ""
        reset = Fore.RESET if colored else ""
        yellow = Fore.YELLOW if colored else ""

        if details:
            return f"{green}%(asctime)s{reset} - {cyan}%(name)s:%(funcName)s:%(lineno)d{reset} - {yellow}%(threadName)s{reset} - %(levelname)s - %(message)s"
        else:
            return f"{green}%(asctime)s{reset} - {cyan}%(name)s{reset} - {yellow}%(threadName)s{reset} - %(levelname)s - %(message)s"

    # Set up logging
    if not args.colorless:
        logging.addLevelName(logging.CRITICAL, f"{Fore.RED}{logging.getLevelName(logging.CRITICAL)}{Fore.RESET}")
        logging.addLevelName(logging.ERROR, f"{Fore.RED}{logging.getLevelName(logging.ERROR)}{Fore.RESET}")
        logging.addLevelName(logging.WARNING, f"{Fore.YELLOW}{logging.getLevelName(logging.WARNING)}{Fore.RESET}")
        logging.addLevelName(logging.INFO, f"{Fore.GREEN}{logging.getLevelName(logging.INFO)}{Fore.RESET}")
        logging.addLevelName(logging.DEBUG, f"{Fore.CYAN}{logging.getLevelName(logging.DEBUG)}{Fore.RESET}")

    logging.getLogger().setLevel(logging.getLevelName(args.log.upper()))
    # Output to file
    if args.log_file is not None:
        handler = logging.FileHandler(args.log_file)
    else:
        handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(get_format_string(not args.colorless, args.log == "debug")))
    logging.getLogger().addHandler(handler)

def parse_args():
    import argparse

    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, prog=os.path.basename(__file__))
    parser.description = __description__
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--log-file", type=str, help="Log file")
    parser.add_argument("-l", "--log", type=str, default="info", choices=["debug", "info", "warning", "error", "critical"],
                        help="Log level. Note: 'debug' log level may print sensitive information,\n"
                             "produce a lot of output and program may run slower/incorectly")
    parser.add_argument("--colorless", action="store_true", help="Disable colored output")

    parser.add_argument("-w", "--workdir", type=str, help="Working directory")
    parser.add_argument("--music-font", type=str, help="Font containing music symbols")

    return parser.parse_args()


def lookup_resource(workdir: Optional[str], name: str):
    path_to_search = [
        ".",
        "resources",
        "../resources",
        "../../resources",
        "../../../resources",
    ]

    if workdir is None:
        workdir = os.path.dirname(__file__)

    for path in path_to_search:
        full_path = os.path.join(workdir, path, name)
        logging.debug("Looking for %s", full_path)
        if os.path.exists(full_path):
            return full_path

    return None

class Settings:
    def __init__(self):
        self.display_timer: bool = True
        self.display_score: bool = True
        self.enable_helpers: bool = False
        self.allow_accidentals: bool = True
        self.notes_per_round: int = 1
        self.allowed_notes_range: Tuple[Note, Note] = (Note(Note.NOTE_G, 2), Note(Note.NOTE_F, 4))
        self.allowed_scales: List[Scale] = [Scale.C_MAJOR]

        self.use_midi_input: bool = False
        self.midi_device: str = ""
        self.midi_channel: int = 0
        self.midi_ignore_octave: bool = False

        self.use_keyboard: bool = False
        self.keyboard_piano_like_layout: bool = False


class SettingsWindow(QDialog):
    def __init__(self, settings: Settings, music_font: SMUFLFont):
        super().__init__()

        self.__flat_glyph = music_font.promise_glyph("accidentalFlat")
        self.__sharp_glyph = music_font.promise_glyph("accidentalSharp")

        logging.info("Settings window")
        self.setWindowTitle("Settings")

        main_layout = QVBoxLayout()
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)

        # Setup challenge settings
        challenge_widget = QWidget()
        challenge_layout = QVBoxLayout()
        challenge_widget.setLayout(challenge_layout)
        challenge_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        tab_widget.addTab(challenge_widget, "Challenge")
        self.display_timer_checkbox = QCheckBox("Display timer")
        self.display_timer_checkbox.setChecked(settings.display_timer)
        challenge_layout.addWidget(self.display_timer_checkbox)
        self.display_score_checkbox = QCheckBox("Display score")
        self.display_score_checkbox.setChecked(settings.display_score)
        challenge_layout.addWidget(self.display_score_checkbox)
        self.enable_helpers = QCheckBox("Enable helpers")
        self.enable_helpers.setChecked(settings.enable_helpers)
        challenge_layout.addWidget(self.enable_helpers)
        challenge_layout.addWidget(label := QLabel("Helpers will display note names on the stave"))
        label.setStyleSheet("color: gray")
        self.allow_accidentals = QCheckBox("Allow accidentals")
        self.allow_accidentals.setChecked(settings.allow_accidentals)
        challenge_layout.addWidget(self.allow_accidentals)
        challenge_layout.addWidget(label := QLabel("Enables use of sharps, flats and naturals during the challenge"))
        label.setStyleSheet("color: gray")

        def create_labeled_widget(label: str, widget: QWidget) -> QWidget:
            labeled_widget = QWidget()
            labeled_layout = QHBoxLayout()
            labeled_layout.setContentsMargins(0, 0, 0, 0)
            labeled_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
            labeled_widget.setLayout(labeled_layout)
            labeled_layout.addWidget(QLabel(label))
            labeled_layout.addWidget(widget)
            return labeled_widget

        self.notes_pre_round_spinbox = QSpinBox()
        self.notes_pre_round_spinbox.setValue(settings.notes_per_round)
        self.notes_pre_round_spinbox.setMinimum(1)
        self.notes_pre_round_spinbox.setMaximum(6)
        challenge_layout.addWidget(create_labeled_widget("Notes per round:", self.notes_pre_round_spinbox))
        challenge_layout.addWidget(label := QLabel("Number of notes that player needs to guess in one round before moving to the next round.\n"
                                                    "Note, that if you are using mouse input, you will need to click on the all notes separately.\n"
                                                    "When using MIDI or keyboard input, you will need to play all notes in the same round"))

        label.setStyleSheet("color: gray")

        challenge_layout.addWidget(QLabel("Allowed notes range:"))

        # Setup range selector settings
        def create_range_selector(clef: Clef):
            # Select allowed range
            widget = QWidget()
            layout = QHBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            widget.setLayout(layout)
            challenge_layout.addWidget(widget, 0, Qt.AlignmentFlag.AlignTop)

            stave = Stave(self, music_font, (-5, 5), 7, 11)
            stave.set_clef(clef)
            stave.set_base_height()
            stave.set_width(200)
            layout.addWidget(stave)

            bottom_button_widget = QWidget()
            bottom_button_layout = QVBoxLayout()
            bottom_button_layout.setContentsMargins(0, 0, 0, 0)
            bottom_button_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            bottom_button_widget.setLayout(bottom_button_layout)
            bottom_button_layout.addWidget(QPushButton("Up"))
            bottom_button_layout.addWidget(QPushButton("Down"))
            bottom_button_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

            layout.addWidget(bottom_button_widget)

        create_range_selector(Clef.TREBLE)
        create_range_selector(Clef.BASS)

        # Setup scale-selector settings
        scale_selector_widget = QWidget()
        scale_selector_layout = QVBoxLayout()
        scale_selector_widget.setLayout(scale_selector_layout)
        tab_widget.addTab(scale_selector_widget, "Scale selector")
        scale_selector_layout.addWidget(QLabel("Select scales that will be used during the challenge"))

        scale_selector_grid_widget = QWidget()
        scale_selector_grid_layout = QGridLayout()
        scale_selector_grid_widget.setLayout(scale_selector_grid_layout)
        scale_selector_layout.addWidget(scale_selector_grid_widget)

        self.scale_checkboxes = {}
        def add_scale_selector(scale: Scale, row: int, col: int):
            selection_widget = QWidget()
            selection_layout = QVBoxLayout()
            selection_layout.setContentsMargins(0, 0, 0, 0)
            selection_widget.setLayout(selection_layout)
            scale_selector_grid_layout.addWidget(selection_widget, row, col)

            scale_stave = Stave(self, music_font, (-5, 5), 7, 11)
            scale_stave.set_clef(Clef.TREBLE)
            scale_stave.set_scale(scale)
            scale_stave.set_base_height()
            scale_stave.set_width(60 + (len(scale.sharps()) + len(scale.flats()) * 25))
            selection_layout.addWidget(scale_stave)

            name = scale.name()
            checkbox = QCheckBox(f"{name}")
            selection_layout.addWidget(checkbox)
            if scale in settings.allowed_scales:
                checkbox.setChecked(True)
            self.scale_checkboxes[scale] = checkbox

        add_scale_selector(Scale.C_MAJOR, 0, 0)
        add_scale_selector(Scale.G_MAJOR, 0, 1)
        add_scale_selector(Scale.D_MAJOR, 0, 2)
        add_scale_selector(Scale.A_MAJOR, 0, 3)
        add_scale_selector(Scale.E_MAJOR, 1, 0)
        add_scale_selector(Scale.B_MAJOR, 1, 1)
        add_scale_selector(Scale.F_SHARP_MAJOR, 1, 2)
        add_scale_selector(Scale.C_SHARP_MAJOR, 1, 3)
        add_scale_selector(Scale.F_MAJOR, 2, 1)
        add_scale_selector(Scale.B_FLAT_MAJOR, 2, 2)
        add_scale_selector(Scale.E_FLAT_MAJOR, 2, 3)
        add_scale_selector(Scale.A_FLAT_MAJOR, 3, 0)
        add_scale_selector(Scale.D_FLAT_MAJOR, 3, 1)
        add_scale_selector(Scale.G_FLAT_MAJOR, 3, 2)
        add_scale_selector(Scale.C_FLAT_MAJOR, 3, 3)

        # Input selection tab
        input_widget = QWidget()
        input_layout = QVBoxLayout()
        input_widget.setLayout(input_layout)
        input_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        tab_widget.addTab(input_widget, "Input")

        midi_box = QGroupBox("MIDI Settings")
        self.use_midi_input_checkbox = QCheckBox("Use MIDI Input")
        self.use_midi_input_checkbox.stateChanged.connect(lambda state: midi_box.setEnabled(state))
        self.use_midi_input_checkbox.setChecked(settings.use_midi_input)
        midi_box.setEnabled(settings.use_midi_input)
        input_layout.addWidget(self.use_midi_input_checkbox)
        midi_layout = QVBoxLayout()
        midi_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        midi_box.setLayout(midi_layout)
        input_layout.addWidget(midi_box)
        self.midi_device_combobox = QComboBox()
        self.midi_device_combobox.addItem("Device 1")
        self.midi_device_combobox.addItem("Device 2")
        self.midi_device_combobox.setCurrentIndex(0)
        midi_layout.addWidget(create_labeled_widget("Device:", self.midi_device_combobox))
        self.midi_channel_spinbox = QSpinBox()
        self.midi_channel_spinbox.setValue(settings.midi_channel)
        midi_layout.addWidget(create_labeled_widget("Channel:", self.midi_channel_spinbox))
        self.midi_ignore_octave_checkbox = QCheckBox("Ignore octave")
        self.midi_ignore_octave_checkbox.setChecked(settings.midi_ignore_octave)
        midi_layout.addWidget(self.midi_ignore_octave_checkbox)
        midi_layout.addWidget(label := QLabel("Ignore octave will ignore octave information from MIDI input\n"
                                                "and will play notes in the same octave as displayed on the stave"))
        label.setStyleSheet("color: gray")

        keyboard_box = QGroupBox("Keyboard Settings")
        self.use_keyboard_checkbox = QCheckBox("Use Keyboard")
        self.use_keyboard_checkbox.stateChanged.connect(lambda state: keyboard_box.setEnabled(state))
        self.use_keyboard_checkbox.setChecked(settings.use_keyboard)
        keyboard_box.setEnabled(settings.use_keyboard)
        input_layout.addWidget(self.use_keyboard_checkbox)
        keyboard_layout = QVBoxLayout()
        keyboard_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        keyboard_box.setLayout(keyboard_layout)
        input_layout.addWidget(keyboard_box)
        self.keyboard_piano_like_layout_checkbox = QCheckBox("Use Piano-like layout")
        self.keyboard_piano_like_layout_checkbox.setChecked(settings.keyboard_piano_like_layout)
        keyboard_layout.addWidget(self.keyboard_piano_like_layout_checkbox)
        keyboard_layout.addWidget(label := QLabel("Piano-like layout is type of input when keyboard keys\n"
                                            "are mapped to piano keys following the same type of layout\n"
                                            "as piano keys. A is mapped to C4, W is mapped to C#4, S is mapped to D4, etc."))
        label.setStyleSheet("color: gray")
        self.keyboard_note_by_char_mode = QRadioButton("Note-by-char mode")
        self.keyboard_note_by_char_mode.setChecked(not settings.keyboard_piano_like_layout)
        keyboard_layout.addWidget(self.keyboard_note_by_char_mode)
        keyboard_layout.addWidget(label := QLabel("Note-by-char mode is type of input when you need to enter\n"
                                         "notes by typing characters. For example for note C4 you need to type 'c'"))
        label.setStyleSheet("color: gray")

        # Setup buttons
        button_widget = QWidget()
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        button_layout.addWidget(QPushButton("Cancel", clicked=self.reject))
        button_layout.addWidget(QPushButton("Apply", clicked=self.accept))
        button_widget.setLayout(button_layout)
        main_layout.addWidget(button_widget)
        # Make buttons take left space
        # button_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.setLayout(main_layout)

    def get_settings(self) -> Settings:
        settings = Settings()
        settings.display_timer = self.display_timer_checkbox.isChecked()
        settings.display_score = self.display_score_checkbox.isChecked()
        settings.enable_helpers = self.enable_helpers.isChecked()
        settings.allow_accidentals = self.allow_accidentals.isChecked()
        settings.notes_per_round = self.notes_pre_round_spinbox.value()
        settings.allowed_scales = [scale for scale, checkbox in self.scale_checkboxes.items() if checkbox.isChecked()]

        settings.use_midi_input = self.use_midi_input_checkbox.isChecked()
        settings.midi_device = self.midi_device_combobox.currentText()
        settings.midi_channel = self.midi_channel_spinbox.value()
        settings.midi_ignore_octave = self.midi_ignore_octave_checkbox.isChecked()

        settings.use_keyboard = self.use_keyboard_checkbox.isChecked()
        settings.keyboard_piano_like_layout = self.keyboard_piano_like_layout_checkbox.isChecked()

        return settings

class Challenge:
    def __init__(self, stave_treble: Stave, stave_bass: Stave):
        self.__stave_treble = stave_treble
        self.__stave_bass = stave_bass

        self.__correct_answers = 0
        self.__total_answers = 0

    def new_round(self, settings: Settings) -> bool:
        pass

    def get_correct_answers(self) -> int:
        pass

    def get_total_answers(self) -> int:
        pass

    def feed_note_start(self, note: Note) -> bool:
        pass

    def feed_note_end(self, note: Note) -> bool:
        pass

class NoterGUI(QWidget):
    def __game_start(self):
        self.__challenge.new_round(self.__settings)
        self.start_button.setText("End")
        self.start_button.setStyleSheet("background-color: #98FB98")

    def __game_end(self):
        self.start_button.setText("Start")
        self.start_button.setStyleSheet("background-color: #FF6347")

    def __init_ui(self):
        self.__stave1.set_base_height()
        self.__stave1.set_width(self.width() * 0.9)
        self.__stave2.set_base_height()
        self.__stave2.set_width(self.width() * 0.9)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.status_label = QLabel()
        self.status_label.hide()
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.status_label.setStyleSheet("font-size: 12pt")
        layout.addWidget(self.status_label, 0, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.__stave1, 0, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.__stave2, 0, Qt.AlignmentFlag.AlignTop)

        self.start_button = QPushButton("Start")
        self.start_button.setMinimumHeight(50)
        self.start_button.clicked.connect(lambda: self.__game_start())
        layout.addWidget(self.start_button, 0, Qt.AlignmentFlag.AlignTop)

        settings_button = QPushButton("Settings")
        def open_settings():
            win = SettingsWindow(self.__settings, self.__music_font)
            if win.exec() == QDialog.DialogCode.Accepted:
                logging.info("Settings accepted")
                self.__settings = win.get_settings()
                self.__stave1.set_draw_helpers(self.__settings.enable_helpers)
                self.__stave2.set_draw_helpers(self.__settings.enable_helpers)
                self.update()

        settings_button.clicked.connect(lambda: open_settings())
        layout.addWidget(settings_button, 0, Qt.AlignmentFlag.AlignTop)

        # Create keyboard
        keyboard = QWidget()
        keyboard_layout = QGridLayout()
        keyboard.setEnabled(False)
        keyboard_layout.setContentsMargins(0, 0, 0, 0)
        keyboard.setLayout(keyboard_layout)
        layout.addWidget(keyboard)
        def add_button(name: str, row: int, col: int):
            button = QPushButton(name)
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            keyboard_layout.addWidget(button, row, col)

            # Resize buttons automatically
            keyboard_layout.setColumnStretch(col, 1)
            keyboard_layout.setRowStretch(row, 1)
            keyboard_layout.setRowMinimumHeight(row, 50)

        add_button("C", 1, 1)
        add_button("D", 1, 2)
        add_button("E", 1, 3)
        add_button("F", 1, 4)
        add_button("G", 1, 5)
        add_button("A", 1, 6)
        add_button("B", 1, 7)
        add_button("C#", 0, 1)
        add_button("D#", 0, 2)
        add_button("E#", 0, 3)
        add_button("F#", 0, 4)
        add_button("G#", 0, 5)
        add_button("A#", 0, 6)
        add_button("B#", 0, 7)
        add_button("Cb", 2, 1)
        add_button("Db", 2, 2)
        add_button("Eb", 2, 3)
        add_button("Fb", 2, 4)
        add_button("Gb", 2, 5)
        add_button("Ab", 2, 6)
        add_button("Bb", 2, 7)
        keyboard.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.setLayout(layout)
        self.__game_end()

    def __init__(self, music_font: SMUFLFont):
        super().__init__()

        self.__settings = Settings()

        self.__stave1 = Stave(self, music_font, (-1, 1), 10, 3)
        self.__stave1.set_clef(Clef.TREBLE)
        self.__stave1.set_scale(Scale.A_MAJOR)

        self.__stave2 = Stave(self, music_font, (-1, 1), 10, 8)
        self.__stave2.set_clef(Clef.BASS)
        self.__stave2.set_scale(Scale.C_MAJOR)

        self.__challenge = Challenge(self.__stave1, self.__stave2)

        self.__music_font = music_font
        if not self.__music_font.load_font():
            raise Exception("Failed to load music font")

    def resizeEvent(self, a0):
        self.__stave1.set_width(self.width() * 0.9)
        self.__stave2.set_width(self.width() * 0.9)
        super().resizeEvent(a0)

    def show(self):
        self.__init_ui()
        super().show()

def main():
    args = parse_args()
    setup_logging(args)

    logging.info("Noter. Version: %s", __version__)

    # Construct QApplication
    app = QApplication([])

    # Determine what music font to use
    if args.music_font is None:
        music_font_path = lookup_resource(args.workdir, "Bravura.otf")
        if music_font_path is None:
            logging.error("Music font not found")
            return
    else:
        music_font_path = args.music_font
    logging.info("Music font: %s", music_font_path)

    # Try to find glyphnames.json
    glyphnames_path = lookup_resource(args.workdir, "glyphnames.json")
    if glyphnames_path is None:
        logging.error("Glyphnames not found")
        return
    logging.info("Glyphnames path: %s", glyphnames_path)

    logging.info("Starting GUI")
    window = NoterGUI(SMUFLFont(glyphnames_path, music_font_path, 64))
    window.setWindowTitle("Noter. Version: " + __version__)

    # Make a window in I3 to look a little bit better.
    # Hoping this will work on other window managers as well.
    if os.environ.get("DESKTOP_SESSION") == "i3":
        logging.info("Detected i3 window manager, setting dialog flag")
        window.setWindowFlag(Qt.WindowType.Dialog, True)

    window.show()
    app.exec()

if __name__ == '__main__':
    main()
