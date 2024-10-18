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
from typing import Optional, Any, List

__description__ = ""
__version__ = "0.1.0"

from PyQt6.QtGui import QFont, QFontMetrics
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QApplication


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

    def __init__(self, glyphnames: str, font_path: str):
        self.__font_path = font_path
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
            # Windows QT does not work well with
            # fonts that are not installed
            if platform.system() == "Windows":
                font_name = os.path.basename(self.__font_path)
                font_name = os.path.splitext(font_name)[0].lower()

                import winreg
                def find_font(reg) -> bool:
                    key = winreg.OpenKey(reg, r'SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts', 0, winreg.KEY_READ)
                    for i in range(0, winreg.QueryInfoKey(key)[1]):
                        tuple = winreg.EnumValue(key, i)
                        if font_name in tuple[1].lower():
                            logging.info("Font is installed: %s", tuple)
                            return True

                    return False

                # Check that Font is installed
                if (not find_font(winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE))
                        and not find_font(winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER))):
                    logging.warning("Font is not installed. QT may not render it correctly")
                    self.__font = QFont(self.__font_path)
                else:
                    self.__font = QFont(font_name)
            else:
                self.__font = QFont(self.__font_path)
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

class NoterGUI(QWidget):
    def __init_ui(self):
        str = " ".join(x.glyph() for x in self.__music_font.get_promised_glyphs())
        hello = QLabel(str, self)
        hello.setFont(self.__music_font.font())

        # Make font bigger
        hello.setStyleSheet("font-size: 100px")
        layout = QVBoxLayout()

        layout.addWidget(hello)
        self.setLayout(layout)

    def __init__(self, music_font: SMUFLFont):
        super().__init__()

        self.__symbol_treble_clef = music_font.promise_glyph("gClef")
        self.__symbol_bass_clef = music_font.promise_glyph("fClef")

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

        if not music_font.load_font():
            raise Exception("Failed to load music font")
        self.__music_font = music_font

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
    window = NoterGUI(SMUFLFont(glyphnames_path, music_font_path))
    window.setWindowTitle("Noter. Version: " + __version__)
    window.show()
    app.exec()

if __name__ == '__main__':
    main()
