#!/usr/bin/env python3

#
# @file stave.py
# @date 22-10-2024
# @author Maxim Kurylko <vk_vm@ukr.net>
#

import logging
from math import ceil
from typing import Tuple, Optional

from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor, QPen, QFont, QPainter
from PyQt6.QtWidgets import QFrame, QWidget

from music import Clef, Scale, TimeSignature, Note
from smufl import SMUFLFont, GlyphPromise

logger = logging.getLogger(__name__)

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

        logger.warning("Note is not in scale: %s", note)
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
        def draw_and_offset(line: float, promise: GlyphPromise, x_offset: float) -> float:
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
                logger.warning("Note is out of bounds: %s", note)
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
            # TODO: Find a way to draw text in the middle of the line
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
