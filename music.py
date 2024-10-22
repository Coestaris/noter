#!/usr/bin/env python3

#
# @file music.py
# @date 22-10-2024
# @author Maxim Kurylko <vk_vm@ukr.net>
#

from enum import Enum
from typing import List

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

    @staticmethod
    def number_to_name(note: int) -> str:
        names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        return names[note % 12]

    @staticmethod
    def sharp(note: int) -> int:
        return (note + 1) % 12

    @staticmethod
    def flat(note: int) -> int:
        return (note - 1) % 12

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

