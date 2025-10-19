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
        self.events = {}
        for name in names:
            self.events[name] = []


    def __call__(self, name, function):
        if name not in self.events:
            raise ValueError('Name "%s" not registered' % name)

        self.events[name].append(function)


    def trigger(self, name, value='NO_VALUE'):
        if name not in self.events:
            raise ValueError('Name "%s" not registered' % name)

        if value == 'NO_VALUE':
            for function in self.events[name]:
                function()
        else:
            for function in self.events[name]:
                function(value)