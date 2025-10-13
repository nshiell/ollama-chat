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

class Bindings:
    def __init__(self, names):
        self.events = d = dict.fromkeys(names, [])


    def __call__(self, name, function):
        if name not in self.events:
            raise ValueError('Name "%s" not registered' % name)

        self.events[name].append(function)


    def trigger(self, name):
        if name not in self.events:
            raise ValueError('Name "%s" not registered' % name)

        for function in self.events[name]:
            function()