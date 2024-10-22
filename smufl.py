#!/usr/bin/env python3

#
# @file smufl.py
# @date 22-10-2024
# @author Maxim Kurylko <vk_vm@ukr.net>
#

import json
import logging
from typing import Any, Optional, List
from PyQt6.QtGui import QFont, QFontMetrics, QFontDatabase

logger = logging.getLogger(__name__)

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

class SMUFLFont:
    @staticmethod
    def __load_metadata(glyphnames: str):
        with open(glyphnames, "r") as f:
            glyphnames = json.load(f)

            metadata = {}
            for name, val in glyphnames.items():
                if val is None:
                    continue

                if name in metadata:
                    logger.warning("Duplicate glyph name: %s", name)

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
        logger.info("Found %d symbols of SMUFL metadata", len(self.__metadata))

        self.__promised_glyphs: List[GlyphPromise] = []

    def promise_glyph(self, name: str) -> GlyphPromise:
        # If glyph is already loaded, return it
        for promise in self.__promised_glyphs:
            if promise.name == name:
                return promise

        promise = GlyphPromise(name)
        self.__promised_glyphs.append(promise)
        return promise

    def font(self) -> QFont:
        return self.__font

    def load_font(self) -> bool:
        try:
            id = QFontDatabase.addApplicationFont(self.__font_path)
            family = QFontDatabase.applicationFontFamilies(id)[0]
            self.__font = QFont(family, self.__font_size)
        except Exception as e:
            logger.error("Failed to load font: %s", e)
            return False

        # Log font information
        logger.info("Font family: %s", self.__font.family())
        logger.info("Font style: %s", self.__font.styleName())
        logger.info("Font weight: %d", self.__font.weight())
        logger.info("Font size: %d", self.__font.pointSize())

        # Make sure that metadata contains required symbols
        for promise in self.__promised_glyphs:
            if promise.name not in self.__metadata:
                logger.error("Metadata does not contain promised glyph: %s", promise.name)
                return False

        # Load required glyphs and cache them
        for promise in self.__promised_glyphs:
            if not self.__check_glyph(promise.name):
                logger.error("Font does not contain promised glyph: %s", promise.name)
                return False
            promise.load(self.__font, self.__metadata[promise.name])

        return True
