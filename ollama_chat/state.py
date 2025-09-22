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
import json
from appdirs import *
from os import path

dirs = AppDirs('ollama-chat', 'nshiell')
user_config_file_path = os.path.join(dirs.user_config_dir, 'config.json')


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


class State:
    attributes = ['model_name', 'style', 'context', 'url', 'font', 'font_size']

    def __init__(self, default_model=None, colour_scheme=None):
        self.model_name = 'mistral-nemo:latest'
        self.style = 'Blue'
        self.context = 'You are being used for the programmer in building the application'
        self.url = 'http://127.0.0.1:11434'
        self.font = 'Ubuntu'
        self.font_size = 12
        self.bind = Bindings(['changed'])

        load_state(self)


    def update(self, values):
        for att in self.attributes:
            setattr(self, att, values[att] if att in values else self[att])

        save_state(self)
        self.bind.trigger('changed')


    def to_dict(self):
        return {
            'model_name'    : self.model_name,
            'style'         : self.style,
            'context'       : self.context,
            'url'           : self.url,
            'font'          : self.font,
            'font_size'     : self.font_size
        }


def make_config_dir_if_not_exists():
    if not os.path.exists(dirs.user_config_dir):
        os.makedirs(dirs.user_config_dir)


def set_config(data):
    make_config_dir_if_not_exists()
    json_data = json.dumps(data, indent=4, sort_keys=True)
    open(user_config_file_path, "w").write(json_data)


def load_state(state):
    config = get_config()
    if config:
        for att in state.attributes:
            try:
                setattr(state, att, config[att] if att in config else state[att])
            except Exception:
                pass


def save_state(state):
    set_config(state.to_dict())


def get_config():
    if path.exists(user_config_file_path):
        return json.loads(open(user_config_file_path, "r").read())

    return None