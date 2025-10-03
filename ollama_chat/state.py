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
import json, re
from appdirs import *
from os import path, remove
from os.path import join, exists
from .conversation import Conversation
import glob


dirs = AppDirs('ollama-chat', 'nshiell')
user_config_file_path = join(dirs.user_config_dir, 'config.json')

from pprint import pprint

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


class Settings:
    def __init__(self, **kwargs):
        self.items = {
            'model_name' : kwargs['model_name'],
            'style'      : kwargs['style'],
            'context'    : kwargs['context'],
            'url'        : kwargs['url'],
            'font'       : kwargs['font'],
            'font_size'  : kwargs['font_size']
        }

        self.bind = Bindings(['changed'])


    def __setitem__(self, key, item):
        if key in self.items:
            self.items[key] = item
        else:
            raise KeyError('Key: "%s" not in settings' % key)

    def __getitem__(self, key):
        return self.items[key]


    def update(self, *args, **kwargs):
        for value in args:
            for key, item in value.items():
                try:
                    self.__setitem__(key, item)
                except KeyError:
                    pass

        for key, value in kwargs.items():
            try:
                self.__setitem__(key, value)
            except KeyError:
                pass

        self.bind.trigger('changed')

    def __iter__(self):
        for key in self.items:
            yield key, self.items[key]


class State:
    def __init__(self, default_model=None, colour_scheme=None):
        self.settings = Settings(
            model_name='mistral-nemo:latest',
            style='Blue',
            context='You are being used for the programmer in building the application',
            url='http://127.0.0.1:11434',
            font='Ubuntu',
            font_size=12
        )
        self.conversations = []
        load_state(self)


    def update(self, values):
        for att in self.attributes:
            setattr(self, att, values[att] if att in values else self[att])

        self.bind.trigger('changed')


    def __iter__(self):
        for key in self.items:
            yield key, getattr(self, key)


    def save(self):
        save_state(self)



def make_config_dir_if_not_exists():
    if not os.path.exists(dirs.user_config_dir):
        os.makedirs(dirs.user_config_dir)


def set_config(path, data):
    make_config_dir_if_not_exists()
    json_data = json.dumps(dict(data), indent=4, sort_keys=True)
    open(path, "w").write(json_data)


def load_state(state):
    config = get_config()
    if isinstance(config, dict):
        state.settings.update(config)


    glob_path = glob.glob(join(dirs.user_config_dir, '*.conversation.json'))
    for con_path in glob_path:
        try:
            match = re.search(r'^.*/(.*)\.conversation\.json$', con_path)
            name = match.group(1)
            con_data = json.load(open(con_path, 'r'))
            con_data['name'] = name
            state.conversations.append(Conversation(**con_data))

        except Exception as e:
            print(e)
            continue


def delete_file(path):
    if exists(path):
        os.remove(path)


def save_state(state):
    set_config(user_config_file_path, state.settings)
    for con in state.conversations:
        path = join(dirs.user_config_dir, con.name + '.conversation.json')
        if con.mark_for_deletion:
            delete_file(path)
            state.conversations.remove(con)
        elif con.messages:
            set_config(path, con)


def get_config():
    if path.exists(user_config_file_path):
        return json.loads(open(user_config_file_path, "r").read())

    return None
