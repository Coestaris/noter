#!/usr/bin/env python3

#
# @file main.py
# @date 18-10-2024
# @author Maxim Kurylko <vk_vm@ukr.net>
#

import logging
import json
import os
from typing import Optional
from fontTools.ttLib import TTFont

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
    SYMBOL_TREBLE_CLEF = "gClef"
    SYMBOL_BASS_CLEF = "fClef"

    SYMBOL_WHOLE_NOTE = "noteWhole"
    # SYMBOL_HALF_NOTE = "noteHalf"
    # SYMBOL_QUARTER_NOTE = "noteQuarter"
    # SYMBOL_EIGHTH_NOTE = "noteEighth"
    # SYMBOL_SIXTEENTH_NOTE = "note16th"
    # SYMBOL_THIRTY_SECOND_NOTE = "note32nd"

    SYMBOL_SHARP = "accidentalSharp"
    SYMBOL_FLAT = "accidentalFlat"
    SYMBOL_NATURAL = "accidentalNatural"

    SYMBOL_DOT = "augmentationDot"

    @staticmethod
    def __collect_required_symbols():
        # Get variables from class
        return [getattr(SMUFLFont, attr) for attr in dir(SMUFLFont) if attr.startswith("SYMBOL_")]

    def __load_metadata(self, glyphnames: str):
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

    def __load_glyph(self, name: str):
        codepoint = self.__metadata.get(name)
        if codepoint is None:
            return None

        return self.font.getBestCmap().get(codepoint)

    def __init__(self, glyphnames: str, font_path: str):
        self.font_path = font_path
        self.font = None

        # Load SMUFL metadata
        self.__metadata = self.__load_metadata(glyphnames)
        logging.info("Found %d symbols of SMUFL metadata", len(self.__metadata))

        # Collect required symbols
        self.__required_symbols = self.__collect_required_symbols()
        self.__required_glyphs = {}
        logging.info("Required symbols: %s", self.__required_symbols)

    def load_font(self) -> bool:
        try:
            self.font = TTFont(self.font_path)
        except Exception as e:
            logging.error("Failed to load font: %s", e)
            return False

        # Make sure that font contains required symbols
        for symbol in self.__required_symbols:
            if symbol not in self.__metadata:
                logging.error("Metadata does not contain symbol: %s", symbol)
                return False

        for symbol in self.__required_symbols:
            glyph = self.__load_glyph(symbol)
            if glyph is None:
                logging.error("Font does not contain symbol: %s", symbol)
                return False

            self.__required_glyphs[symbol] = glyph

        logging.info("Loaded %d glyphs", len(self.__required_glyphs))
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

def main():
    args = parse_args()
    setup_logging(args)

    logging.info("Noter. Version: %s", __version__)

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

    # Load music font. Must SMUFL compliant font
    music_font = SMUFLFont(glyphnames_path, music_font_path)
    if not music_font.load_font():
        return

if __name__ == '__main__':
    main()
