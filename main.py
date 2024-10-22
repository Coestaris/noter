#!/usr/bin/env python3

#
# @file main.py
# @date 18-10-2024
# @author Maxim Kurylko <vk_vm@ukr.net>
#

import logging
import json
import os
from enum import Enum
from math import ceil
from typing import Optional, Any, List, Tuple

from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QFont, QFontMetrics, QFontDatabase, QPainter, QColor, \
    QPen
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QApplication, QFrame, \
    QSizePolicy, QTabWidget, QCheckBox, QPushButton, QDialog, QHBoxLayout, \
    QGridLayout, QLabel, QSpinBox, QComboBox, QGroupBox, QRadioButton

__description__ = ""
__version__ = "0.1.0"

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

class SMUFLFont:
    class GlyphPromise:
        def __init__(self, name: str):
            self.name = name
            self.__glyph: Any = None
            self.__font: Optional[QFont] = None
            self.__width: float = 0
            self.__height: float = 0

        def load(self, font: QFont, codepoint: int):
            if self.__glyph is not None:
                raise Exception("Glyph is already loaded")

            self.__font = font

            # QT does not provide a way to load glyph by codepoint.
            # It will be loaded and rendered by GUI application
            self.__glyph = chr(codepoint)

            # Calculate width and height
            rect = QFontMetrics(self.__font).boundingRectChar(self.__glyph)
            self.__width = rect.width()
            self.__height = rect.height()

        def glyph(self):
            if self.__glyph is None:
                raise Exception("Glyph is not loaded")
            return self.__glyph

        def width(self) -> float:
            return self.__width

        def height(self) -> float:
            return self.__height

    @staticmethod
    def __load_metadata(glyphnames: str):
        with open(glyphnames, "r") as f:
            glyphnames = json.load(f)

            metadata = {}
            for name, val in glyphnames.items():
                if val is None:
                    continue

                if name in metadata:
                    logging.warning("Duplicate glyph name: %s", name)

                unicode = val["codepoint"] # In format 'U+E602'
                metadata[name] = int(unicode[2:], 16)

        return metadata

    def __check_glyph(self, name: str):
        codepoint = self.__metadata.get(name)
        if codepoint is None:
            return None

        # GUI application is required to load font
        return QFontMetrics(self.__font).inFont(chr(codepoint))

    def __init__(self, glyphnames: str, font_path: str, font_size: float):
        self.__font_path = font_path
        self.__font_size = font_size
        self.__font = None

        # Load SMUFL metadata
        self.__metadata = self.__load_metadata(glyphnames)
        logging.info("Found %d symbols of SMUFL metadata", len(self.__metadata))

        self.__promised_glyphs: List[SMUFLFont.GlyphPromise] = []

    def promise_glyph(self, name: str) -> GlyphPromise:
        # If glyph is already loaded, return it
        for promise in self.__promised_glyphs:
            if promise.name == name:
                return promise

        promise = self.GlyphPromise(name)
        self.__promised_glyphs.append(promise)
        return promise

    # TODO: Temporary solution. Load font in GUI application
    def get_promised_glyphs(self) -> List[GlyphPromise]:
        return self.__promised_glyphs

    def font(self) -> QFont:
        return self.__font

    def load_font(self) -> bool:
        try:
            # # Windows QT does not work well with
            # # fonts that are not installed
            # if platform.system() == "Windows":
            #     font_name = os.path.basename(self.__font_path)
            #     font_name = os.path.splitext(font_name)[0].lower()
            #
            #     import winreg
            #     def find_font(reg) -> bool:
            #         key = winreg.OpenKey(reg, r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts', 0, winreg.KEY_READ)
            #         for i in range(0, winreg.QueryInfoKey(key)[1]):
            #             tuple = winreg.EnumValue(key, i)
            #             if font_name in tuple[1].lower():
            #                 logging.info("Font is installed: %s", tuple)
            #                 return True
            #
            #         return False
            #
            #     # Check that Font is installed
            #     if (not find_font(winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE))
            #             and not find_font(winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER))):
            #         logging.warning("Font is not installed. QT may not render it correctly")
            #         self.__font = QFont(self.__font_path)
            #     else:
            #         self.__font = QFont(font_name)
            # else:
            id = QFontDatabase.addApplicationFont(self.__font_path)
            family = QFontDatabase.applicationFontFamilies(id)[0]
            self.__font = QFont(family, self.__font_size)
        except Exception as e:
            logging.error("Failed to load font: %s", e)
            return False

        # Log font information
        logging.info("Font family: %s", self.__font.family())
        logging.info("Font style: %s", self.__font.styleName())
        logging.info("Font weight: %d", self.__font.weight())
        logging.info("Font size: %d", self.__font.pointSize())

        # Make sure that metadata contains required symbols
        for promise in self.__promised_glyphs:
            if promise.name not in self.__metadata:
                logging.error("Metadata does not contain promised glyph: %s", promise.name)
                return False

        # Load required glyphs and cache them
        for promise in self.__promised_glyphs:
            if not self.__check_glyph(promise.name):
                logging.error("Font does not contain promised glyph: %s", promise.name)
                return False
            promise.load(self.__font, self.__metadata[promise.name])

        return True

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

class Note:
    NOTE_C = 0
    NOTE_C_SHARP = 1
    NOTE_D = 2
    NOTE_D_SHARP = 3
    NOTE_E = 4
    NOTE_F = 5
    NOTE_F_SHARP = 6
    NOTE_G = 7
    NOTE_G_SHARP = 8
    NOTE_A = 9
    NOTE_A_SHARP = 10
    NOTE_B = 11

    # Duration in whole notes
    def __init__(self, note: int, octave: int = 4, duration: float = 1.0, position: float = 0):
        self.note = note
        self.octave = octave
        self.duration = duration
        self.position = position

    def sharp(self):
        self.note += 1
        if self.note > Note.NOTE_B:
            self.note = Note.NOTE_C

    def flat(self):
        self.note -= 1
        if self.note < Note.NOTE_C:
            self.note = Note.NOTE_B

    @staticmethod
    def number_to_name(note: int) -> str:
        names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        return names[note]

    def __str__(self):
        return f"Note(note={Note.number_to_name(self.note)}, octave={self.octave}, duration={self.duration}, position={self.position})"

    def __repr__(self):
        return str(self)

class Scale:
    def __init__(self, name: str, sharps: List[int], flats: List[int]):
        self.__name = name
        self.__sharps = sharps
        self.__flats = flats

    def sharps(self) -> List[Note]:
        return [Note(note) for note in self.__sharps]

    def flats(self) -> List[Note]:
        return [Note(note) for note in self.__flats]

    def name(self) -> str:
        return self.__name

Scale.C_MAJOR = Scale("C Major", [], [])

Scale.G_MAJOR = Scale("G Major", [Note.NOTE_F], [])
Scale.D_MAJOR = Scale("D Major", [Note.NOTE_F, Note.NOTE_C], [])
Scale.A_MAJOR = Scale("A Major", [Note.NOTE_F, Note.NOTE_C, Note.NOTE_G], [])
Scale.E_MAJOR = Scale("E Major", [Note.NOTE_F, Note.NOTE_C, Note.NOTE_G, Note.NOTE_D], [])
Scale.B_MAJOR = Scale("B Major", [Note.NOTE_F, Note.NOTE_C, Note.NOTE_G, Note.NOTE_D, Note.NOTE_A], [])
Scale.F_SHARP_MAJOR = Scale("F-Sharp Major", [Note.NOTE_F, Note.NOTE_C, Note.NOTE_G, Note.NOTE_D, Note.NOTE_A, Note.NOTE_E], [])
Scale.C_SHARP_MAJOR = Scale("C-Sharp Major", [Note.NOTE_F, Note.NOTE_C, Note.NOTE_G, Note.NOTE_D, Note.NOTE_A, Note.NOTE_E, Note.NOTE_B], [])

Scale.F_MAJOR = Scale("F Major", [], [Note.NOTE_B])
Scale.B_FLAT_MAJOR = Scale("B-Flat Major", [], [Note.NOTE_B, Note.NOTE_E])
Scale.E_FLAT_MAJOR = Scale("E-Flat Major", [], [Note.NOTE_B, Note.NOTE_E, Note.NOTE_A])
Scale.A_FLAT_MAJOR = Scale("A-Flat Major", [], [Note.NOTE_B, Note.NOTE_E, Note.NOTE_A, Note.NOTE_D])
Scale.D_FLAT_MAJOR = Scale("D-Flat Major", [], [Note.NOTE_B, Note.NOTE_E, Note.NOTE_A, Note.NOTE_D, Note.NOTE_G])
Scale.G_FLAT_MAJOR = Scale("G-Flat Major", [], [Note.NOTE_B, Note.NOTE_E, Note.NOTE_A, Note.NOTE_D, Note.NOTE_G, Note.NOTE_C])
Scale.C_FLAT_MAJOR = Scale("C-Flat Major", [], [Note.NOTE_B, Note.NOTE_E, Note.NOTE_A, Note.NOTE_D, Note.NOTE_G, Note.NOTE_C, Note.NOTE_F])

class Clef(Enum):
    TREBLE = 0
    BASS = 1
    ALTO = 2

class TimeSignature(Enum):
    SIGNATURE_2_4 = 0
    SIGNATURE_3_4 = 1
    SIGNATURE_4_4 = 2
    SIGNATURE_6_8 = 3
    SIGNATURE_8_8 = 4

class Stave(QFrame):
    def __init__(self, parent: QWidget, music_font: SMUFLFont, allowed_ledger_lines: Tuple[int, int] = (-2, 2), spacing: int = 12, v_offset: float = 3):
        super().__init__(parent)

        self.__music_font = music_font
        self.__allowed_ledger_lines = allowed_ledger_lines

        # Request glyphs from font
        self.__symbol_treble_clef = music_font.promise_glyph("gClef")
        self.__symbol_bass_clef = music_font.promise_glyph("fClef")
        self.__symbol_alto_clef = music_font.promise_glyph("cClef")

        self.__symbol_whole_note = music_font.promise_glyph("noteWhole")
        self.__symbol_half_note_up = music_font.promise_glyph("noteHalfUp")
        self.__symbol_half_note_down = music_font.promise_glyph("noteHalfDown")
        self.__symbol_quarter_note_up = music_font.promise_glyph("noteQuarterUp")
        self.__symbol_quarter_note_down = music_font.promise_glyph("noteQuarterDown")
        self.__symbol_eighth_note_up = music_font.promise_glyph("note8thUp")
        self.__symbol_eighth_note_down = music_font.promise_glyph("note8thDown")

        self.__symbol_sharp = music_font.promise_glyph("accidentalSharp")
        self.__symbol_flat = music_font.promise_glyph("accidentalFlat")
        self.__symbol_natural = music_font.promise_glyph("accidentalNatural")

        self.__time_signature_2_4 = music_font.promise_glyph("timeSig2")
        self.__time_signature_3_4 = music_font.promise_glyph("timeSig3")
        self.__time_signature_4_4 = music_font.promise_glyph("timeSig4")
        self.__time_signature_6_8 = music_font.promise_glyph("timeSig6")
        self.__time_signature_8_8 = music_font.promise_glyph("timeSig8")

        self.__base_size = 30
        self.__spacing = spacing
        self.__v_offset = v_offset

        self.__draw_helpers = False
        self.__clef = Clef.TREBLE
        self.__scale = Scale.C_MAJOR
        self.__time_signature = None
        self.__notes = []

    def __get_line_from_note(self, note: Note) -> Optional[float]:
        # Find note in scale
        for line, n in self.__line_to_note_cache.items():
            if n.note == note.note and n.octave == note.octave:
                return line

        logging.warning("Note is not in scale: %s", note)
        return None

    def __get_note_from_line(self, line: float) -> Optional[Note]:
        return self.__line_to_note_cache.get(line)

    def __build_cache(self):
        if self.__clef == Clef.TREBLE:
            starting_note = 2 # In C major scale steps
            starting_octave = 4
        elif self.__clef == Clef.BASS:
            starting_note = -3
            starting_octave = 3
        elif self.__clef == Clef.ALTO:
            starting_note = 0
            starting_octave = 4

        def get_cycled_note(offset: int) -> Note:
            major_scale = [2, 2, 1, 2, 2, 2, 1]
            n = offset + starting_note
            if n < 0:
                n = 7 + n
            elif n >= 7:
                n = n % 7
            n = sum(major_scale[:n])

            return Note(n % 12, starting_octave + (offset + starting_note) // 7)

        ledger_down_extension = self.__allowed_ledger_lines[0] * 2 - 1 # In scale steps
        ledger_up_extension = self.__allowed_ledger_lines[1] * 2 + 1
        self.__line_to_note_cache = {}
        for n in range(ledger_down_extension, 5 * 2 + ledger_up_extension):
            self.__line_to_note_cache[n / 2] = get_cycled_note(n)

    def __get_line_position(self, line: float) -> float:
        return self.height() / self.__v_offset + 5 * self.__base_size - line * self.__base_size

    # All sizes will be relative to the size of the whole note
    def set_base_height(self, height: float = None):
        if height is None:
            self.__base_size = self.__symbol_whole_note.height()
        else:
            self.__base_size = height

        self.setFixedHeight(int(self.__base_size * self.__spacing))

    def set_width(self, width: float):
        self.setMinimumWidth(int(width))

    def set_draw_helpers(self, draw: bool):
        self.__draw_helpers = draw

    def paintEvent(self, a0):
        painter = QPainter(self)

        painter.setFont(self.__music_font.font())
        painter.setPen(QPen(QColor(0, 0, 0), self.__base_size * 2 / 24))
        painter.setBrush(QColor(0, 0, 0))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # painter.fillRect(0, 0, self.width(), self.height(), QColor(100, 100, 100))

        # Draw stave
        for i in range(5):
            y = self.__get_line_position(i)
            painter.drawLine(
                QPointF(0, y),
                QPointF(self.parent().width(), y))

        # Draw clef
        def draw_and_offset(line: float, promise: SMUFLFont.GlyphPromise, x_offset: float) -> float:
            painter.drawText(QPointF(x_offset, self.__get_line_position(line)), promise.glyph())
            return x_offset + promise.width()

        x_offset = 0
        if self.__clef == Clef.TREBLE:
            x_offset = draw_and_offset(1, self.__symbol_treble_clef, x_offset)
        elif self.__clef == Clef.BASS:
            x_offset = draw_and_offset(2, self.__symbol_bass_clef, x_offset)
        elif self.__clef == Clef.ALTO:
            x_offset = draw_and_offset(2, self.__symbol_alto_clef, x_offset)

        # Draw scale
        flats = self.__scale.flats()
        lines = [4.5, 4.0, 3.5, 3.0, 2.5, 2.0, 1.5, 1.0, 0.5, 0.0]
        for sharp in self.__scale.sharps():
            for line in lines:
                if self.__line_to_note_cache[line].note == sharp.note:
                    x_offset = draw_and_offset(line, self.__symbol_sharp, x_offset)
                    break
        for flat in flats:
            for line in lines:
                if self.__line_to_note_cache[line].note == flat.note:
                    x_offset = draw_and_offset(line, self.__symbol_flat, x_offset)
                    break

        # Draw time signature
        if self.__time_signature:
            if self.__time_signature == TimeSignature.SIGNATURE_2_4:
                x_offset = draw_and_offset(2, self.__time_signature_2_4, x_offset)
            elif self.__time_signature == TimeSignature.SIGNATURE_3_4:
                x_offset = draw_and_offset(2, self.__time_signature_3_4, x_offset)
            elif self.__time_signature == TimeSignature.SIGNATURE_4_4:
                x_offset = draw_and_offset(2, self.__time_signature_4_4, x_offset)
            elif self.__time_signature == TimeSignature.SIGNATURE_6_8:
                x_offset = draw_and_offset(2, self.__time_signature_6_8, x_offset)
            elif self.__time_signature == TimeSignature.SIGNATURE_8_8:
                x_offset = draw_and_offset(2, self.__time_signature_8_8, x_offset)

        x_offset += self.width() * 0.1

        # Draw notes
        left_space = self.width() - x_offset
        for note in self.__notes:
            if note.position + note.duration > 1.0:
                logging.warning("Note is out of bounds: %s", note)
                continue

            line = self.__get_line_from_note(note)
            if line is None:
                continue

            pos_x = x_offset + left_space * note.position
            pos_y = self.__get_line_position(line)
            glyph = None
            if note.duration == 1.0:
                glyph = self.__symbol_whole_note
            elif note.duration == 0.5:
                if self.__clef == Clef.BASS:
                    glyph = self.__symbol_half_note_down
                else:
                    glyph = self.__symbol_half_note_up
            elif note.duration == 0.25:
                if self.__clef == Clef.BASS:
                    glyph = self.__symbol_quarter_note_down
                else:
                    glyph = self.__symbol_quarter_note_up
            elif note.duration == 0.125:
                if self.__clef == Clef.BASS:
                    glyph = self.__symbol_eighth_note_down
                else:
                    glyph = self.__symbol_eighth_note_up

            # Draw ledger lines
            if line <= -1 or line > 4.5:
                ledger_y = self.__get_line_position(ceil(line))
                painter.drawLine(
                    QPointF(pos_x - self.__symbol_whole_note.width() / 3, ledger_y),
                    QPointF(pos_x + self.__symbol_whole_note.width(), ledger_y))

            if glyph is not None:
                painter.drawText(QPointF(pos_x, pos_y), glyph.glyph())

        # Draw helpers
        if self.__draw_helpers:
            painter.setFont(QFont("Arial", 12))
            # Set color to gray
            painter.setPen(QPen(QColor(100, 100, 255)))
            for line in lines:
                x_pos = self.width() - 20
                if line.is_integer():
                    x_pos -= 20
                y_pos = self.__get_line_position(line)
                note = self.__get_note_from_line(line)
                painter.drawText(QPointF(x_pos, y_pos), f"{Note.number_to_name(note.note)}")

            painter.setFont(self.__music_font.font())

        super().paintEvent(a0)

    def set_clef(self, clef : Clef) -> None:
        self.__clef = clef
        self.__build_cache()

    def set_scale(self, scale: Scale) -> None:
        self.__scale = scale
        self.__build_cache()

    def set_time_signature(self, time_signature: TimeSignature) -> None:
        self.__time_signature = time_signature

    def put_note(self, note: Note) -> None:
        self.__notes.append(note)

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

class NoterGUI(QWidget):
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
        # Make background color pale green
        self.start_button.setStyleSheet("background-color: #98FB98")
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

    def __init__(self, music_font: SMUFLFont):
        super().__init__()

        self.__settings = Settings()

        self.__stave1 = Stave(self, music_font, (-1, 1), 10, 3)
        self.__stave1.set_clef(Clef.TREBLE)
        self.__stave1.set_scale(Scale.A_MAJOR)

        self.__stave2 = Stave(self, music_font, (-1, 1), 10, 8)
        self.__stave2.set_clef(Clef.BASS)
        self.__stave2.set_scale(Scale.C_MAJOR)

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
