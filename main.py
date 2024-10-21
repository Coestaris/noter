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
from typing import Optional, Any, List

__description__ = ""
__version__ = "0.1.0"

from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QFont, QFontMetrics, QFontDatabase, QPainter, QColor, \
    QPixmap
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication, QFrame


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
        def __init__(self, font: QFont, name: str):
            self.name = name
            self.__font = font
            self.__glyph: Any = None

        def load(self, codepoint: int):
            if self.__glyph is not None:
                raise Exception("Glyph is already loaded")

            # QT does not provide a way to load glyph by codepoint.
            # It will be loaded and rendered by GUI application
            self.__glyph = chr(codepoint)

        def glyph(self):
            if self.__glyph is None:
                raise Exception("Glyph is not loaded")
            return self.__glyph

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
        promise = self.GlyphPromise(self.__font, name)
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
            promise.load(self.__metadata[promise.name])

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
    def __init__(self, note: int, octave: int = 4, duration: float = 1.0, position: int = 0):
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
    def __init__(self, parent: QWidget, music_font: SMUFLFont):
        super().__init__(parent)

        self.__music_font = music_font

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

    # All sizes will be relative to the size of the whole note
    def set_base_height(self, height: float = None):
        if height is None:
            rect = QFontMetrics(self.__music_font.font()).boundingRectChar(
                self.__symbol_whole_note.glyph())
            self.__base_size = rect.height()
        else:
            self.__base_size = height

        self.setMinimumSize(self.width(), self.__base_size * 5)

    def set_width(self, width: float):
        self.setMinimumSize(int(width), self.height())

    def __get_line_position(self, line: int) -> float:
        return 5 * self.__base_size - line * self.__base_size

    def paintEvent(self, a0):
        painter = QPainter(self)

        painter.setFont(self.__music_font.font())
        painter.setPen(QColor(0, 0, 0))
        painter.setBrush(QColor(0, 0, 0))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # Draw stave
        for i in range(5):
            painter.drawLine(
                QPointF(0, i * self.__base_size),
                QPointF(self.parent().width(), i * self.__base_size))

        # Draw clef
        if self.__clef == Clef.TREBLE:
            painter.drawText(0, self.__get_line_position(2), self.__symbol_treble_clef.glyph())
        elif self.__clef == Clef.BASS:
            painter.drawText(0, self.__get_line_position(2), self.__symbol_bass_clef.glyph())
        elif self.__clef == Clef.ALTO:
            painter.drawText(0, self.__get_line_position(2), self.__symbol_alto_clef.glyph())

        super().paintEvent(a0)

    def set_clef(self, clef : Clef) -> None:
        self.__clef = clef

    def set_scale(self, scale: Scale) -> None:
        self.__scale = scale

    def set_time_signature(self, time_signature: TimeSignature) -> None:
        self.__time_signature = time_signature

    def put_note(self, note: Note) -> None:
        self.__notes.append(note)

class NoterGUI(QWidget):
    def __init_ui(self):
        self.setMinimumSize(800, 600)
        self.__stave.set_base_height()
        self.__stave.set_width(self.width() * 0.9)

        layout = QVBoxLayout()
        layout.addWidget(self.__stave, 0, Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

    def __init__(self, music_font: SMUFLFont):
        super().__init__()
        self.__stave = Stave(self, music_font)

        if not music_font.load_font():
            raise Exception("Failed to load music font")

    def resizeEvent(self, a0):
        self.__stave.set_width(self.width() * 0.9)
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
