"""
    Database Dossier - A User Interface for your databases
    Copyright (C) 2025  Nicholas Shiell

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

class State:
    def __init__(self, default_model=None, colour_scheme=None):
    #    self.default_model = default_model
    #    self.colour_scheme = colour_scheme

    #def load(self):
        self.default_model = 'mistral-nemo:latest'
        self.style = 'Blue'
        self.context = 'You are being used for the programmer in building the application'
        self.url = 'http://127.0.0.1:11434'
        self.font = 'Ubuntu'
        self.font_size = 12