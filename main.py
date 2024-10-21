#!/usr/bin/env python3

#
# @file main.py
# @date 18-10-2024
# @author Maxim Kurylko <vk_vm@ukr.net>
#

import logging
import json
import os
import platform
from enum import Enum
from math import floor, ceil
from typing import Optional, Any, List, Tuple

__description__ = ""
__version__ = "0.1.0"

from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QFont, QFontMetrics, QFontDatabase, QPainter, QColor, \
    QPen
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QApplication, QFrame, \
    QSizePolicy


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
    def __init__(self, sharps: List[int], flats: List[int]):
        self.sharps = sharps
        self.flats = flats

    def sharps(self) -> List[Note]:
        return [Note(note) for note in self.sharps]

    def flats(self) -> List[Note]:
        return [Note(note) for note in self.flats]


Scale.C_MAJOR = Scale([], [])

Scale.G_MAJOR = Scale([Note.NOTE_F], [])
Scale.D_MAJOR = Scale([Note.NOTE_F, Note.NOTE_C], [])
Scale.A_MAJOR = Scale([Note.NOTE_F, Note.NOTE_C, Note.NOTE_G], [])
Scale.E_MAJOR = Scale([Note.NOTE_F, Note.NOTE_C, Note.NOTE_G, Note.NOTE_D], [])
Scale.B_MAJOR = Scale([Note.NOTE_F, Note.NOTE_C, Note.NOTE_G, Note.NOTE_D, Note.NOTE_A], [])
Scale.F_SHARP_MAJOR = Scale([Note.NOTE_F, Note.NOTE_C, Note.NOTE_G, Note.NOTE_D, Note.NOTE_A, Note.NOTE_E], [])
Scale.C_SHARP_MAJOR = Scale([Note.NOTE_F, Note.NOTE_C, Note.NOTE_G, Note.NOTE_D, Note.NOTE_A, Note.NOTE_E, Note.NOTE_B], [])
Scale.F_MAJOR = Scale([], [Note.NOTE_B])
Scale.B_FLAT_MAJOR = Scale([], [Note.NOTE_B, Note.NOTE_E])
Scale.E_FLAT_MAJOR = Scale([], [Note.NOTE_B, Note.NOTE_E, Note.NOTE_A])
Scale.A_FLAT_MAJOR = Scale([], [Note.NOTE_B, Note.NOTE_E, Note.NOTE_A, Note.NOTE_D])
Scale.D_FLAT_MAJOR = Scale([], [Note.NOTE_B, Note.NOTE_E, Note.NOTE_A, Note.NOTE_D, Note.NOTE_G])
Scale.G_FLAT_MAJOR = Scale([], [Note.NOTE_B, Note.NOTE_E, Note.NOTE_A, Note.NOTE_D, Note.NOTE_G, Note.NOTE_C])
Scale.C_FLAT_MAJOR = Scale([], [Note.NOTE_B, Note.NOTE_E, Note.NOTE_A, Note.NOTE_D, Note.NOTE_G, Note.NOTE_C, Note.NOTE_F])

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
    def __init__(self, parent: QWidget, music_font: SMUFLFont, allowed_ledger_lines: Tuple[int, int] = (-2, 2)):
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

        self.__clef = Clef.TREBLE
        self.__scale = Scale.C_MAJOR
        self.__time_signature = TimeSignature.SIGNATURE_4_4
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
        return self.height() / 3 + 5 * self.__base_size - line * self.__base_size

    # All sizes will be relative to the size of the whole note
    def set_base_height(self, height: float = None):
        if height is None:
            self.__base_size = self.__symbol_whole_note.height()
        else:
            self.__base_size = height

        self.setMinimumSize(self.width(), int(self.__base_size * 12))

    def set_width(self, width: float):
        self.setMinimumSize(int(width), self.height())

    def paintEvent(self, a0):
        painter = QPainter(self)

        painter.setFont(self.__music_font.font())
        painter.setPen(QPen(QColor(0, 0, 0), self.__base_size * 2 / 24))
        painter.setBrush(QColor(0, 0, 0))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # painter.fillRect(0, 0, self.width(), self.height(), QColor(30, 30, 30))

        # Draw stave
        for i in range(5):
            y = self.__get_line_position(i)
            painter.drawLine(
                QPointF(0, y),
                QPointF(self.parent().width(), y))

        # Draw clef
        x_offset = 0
        if self.__clef == Clef.TREBLE:
            painter.drawText(QPointF(0, self.__get_line_position(1)), self.__symbol_treble_clef.glyph())
            x_offset += self.__symbol_treble_clef.width()
        elif self.__clef == Clef.BASS:
            painter.drawText(QPointF(0, self.__get_line_position(2)), self.__symbol_bass_clef.glyph())
            x_offset += self.__symbol_bass_clef.width()
        elif self.__clef == Clef.ALTO:
            painter.drawText(QPointF(0, self.__get_line_position(2)), self.__symbol_alto_clef.glyph())
            x_offset += self.__symbol_alto_clef.width()

        # Draw scale
        pass

        # Draw time signature
        if self.__time_signature == TimeSignature.SIGNATURE_2_4:
            painter.drawText(QPointF(x_offset, self.__get_line_position(2)), self.__time_signature_2_4.glyph())
            x_offset += self.__time_signature_2_4.width()
        elif self.__time_signature == TimeSignature.SIGNATURE_3_4:
            painter.drawText(QPointF(x_offset, self.__get_line_position(2)), self.__time_signature_3_4.glyph())
            x_offset += self.__time_signature_3_4.width()
        elif self.__time_signature == TimeSignature.SIGNATURE_4_4:
            painter.drawText(QPointF(x_offset, self.__get_line_position(2)), self.__time_signature_4_4.glyph())
            x_offset += self.__time_signature_4_4.width()
        elif self.__time_signature == TimeSignature.SIGNATURE_6_8:
            painter.drawText(QPointF(x_offset, self.__get_line_position(2)), self.__time_signature_6_8.glyph())
            x_offset += self.__time_signature_6_8.width()
        elif self.__time_signature == TimeSignature.SIGNATURE_8_8:
            painter.drawText(QPointF(x_offset, self.__get_line_position(2)), self.__time_signature_8_8.glyph())
            x_offset += self.__time_signature_8_8.width()

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
                glyph = self.__symbol_half_note_up
            elif note.duration == 0.25:
                glyph = self.__symbol_quarter_note_up
            elif note.duration == 0.125:
                glyph = self.__symbol_eighth_note_up

            # Draw ledger lines
            if line <= -1 or line > 4.5:
                ledger_y = self.__get_line_position(ceil(line))
                painter.drawLine(
                    QPointF(pos_x - self.__symbol_whole_note.width() / 3, ledger_y),
                    QPointF(pos_x + self.__symbol_whole_note.width(), ledger_y))

            if glyph is not None:
                painter.drawText(QPointF(pos_x, pos_y), glyph.glyph())

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

class NoterGUI(QWidget):
    def __init_ui(self):
        self.setMinimumSize(800, 600)
        self.__stave1.set_base_height()
        self.__stave1.set_width(self.width() * 0.9)
        self.__stave2.set_base_height()
        self.__stave2.set_width(self.width() * 0.9)

        layout = QVBoxLayout()
        layout.addWidget(self.__stave1, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.__stave2, 0, Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

    def __init__(self, music_font: SMUFLFont):
        super().__init__()

        self.__stave1 = Stave(self, music_font, (-1, 1))
        self.__stave1.set_clef(Clef.TREBLE)
        self.__stave1.set_scale(Scale.C_MAJOR)
        self.__stave1.set_time_signature(TimeSignature.SIGNATURE_8_8)
        self.__stave1.put_note(Note(Note.NOTE_B, 3, 0.125, 7/8))
        self.__stave1.put_note(Note(Note.NOTE_C, 4, 0.125, 0/8))
        self.__stave1.put_note(Note(Note.NOTE_D, 4, 0.125, 1/8))
        self.__stave1.put_note(Note(Note.NOTE_E, 4, 0.125, 2/8))
        self.__stave1.put_note(Note(Note.NOTE_F, 4, 0.125, 3/8))
        self.__stave1.put_note(Note(Note.NOTE_G, 4, 0.125, 4/8))
        self.__stave1.put_note(Note(Note.NOTE_B, 5, 0.125, 5/8))
        self.__stave1.put_note(Note(Note.NOTE_A, 5, 0.125, 6/8))
        self.__stave1.put_note(Note(Note.NOTE_G, 5, 0.125, 7/8))

        self.__stave2 = Stave(self, music_font, (0, 0))
        self.__stave2.set_clef(Clef.BASS)
        self.__stave2.set_scale(Scale.C_MAJOR)
        self.__stave2.set_time_signature(TimeSignature.SIGNATURE_4_4)
        self.__stave2.put_note(Note(Note.NOTE_C, 3, 0.25, 0/4))
        self.__stave2.put_note(Note(Note.NOTE_D, 3, 0.25, 1/4))
        self.__stave2.put_note(Note(Note.NOTE_E, 3, 0.25, 2/4))
        self.__stave2.put_note(Note(Note.NOTE_F, 3, 0.25, 3/4))

        if not music_font.load_font():
            raise Exception("Failed to load music font")

    def resizeEvent(self, a0):
        self.__stave1.set_width(self.width() * 0.9)
        self.__stave2.set_width(self.width() * 0.9)
        super().resizeEvent(a0)

    def show(self):
        super().show()
        self.__init_ui()

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
