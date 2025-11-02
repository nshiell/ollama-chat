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
from __future__ import annotations

import json, re
from appdirs import *
from os import path, remove
from os.path import join, exists
from .conversation import Conversation
from .bindings import Bindings
import glob


def filter_dict(spec:dict, source) -> dict:
    if not isinstance(source, dict):
        return {k: None for k in spec.keys()}

    new_dict = {}
    for name, data_type in spec.items():
        if name in source and isinstance(source[name], data_type):
            new_dict[name] = source[name]
        else:
            new_dict[name] = None

    return new_dict


def try_read_json_file(file_path:str):
    try:
        return json.loads(open(file_path, "r").read())
    except Exception as e:
        print(e)

    return None


class Storage:
    def __init__(self, *, dirs:Optional[AppDirs]=None) -> None:
        self.dir = dirs if dirs else AppDirs('ollama-chat', 'nshiell')
        self.config_file_path = join(self.dir.user_config_dir, 'config.json')
        self._config = None
        #self._conversations = None


    @property
    def config(self):
        if not self._config:
            self._config = try_read_json_file(self.config_file_path)
        return self._config


    @config.setter
    def config(self, config):
        self._config = config
        open(self.config_file_path, "w").write(
            json.dumps(config, indent=4, sort_keys=True)
        )


    def conversations(self):
        if not self._conversations:
            self._conversations = self._load_conversations()

        for conversation_dict in self._conversations:
            yield conversation_dict


    def save_all_conversations(self, conversations:list):
        for con in conversations:
            filename = con.name + '.conversation.json'
            path = join(self.dir.user_config_dir, filename)

            if con.mark_for_deletion:
                if exists(path):
                    remove(path)
            else:
                json_text = json.dumps(dict(con), indent=4, sort_keys=True)
                open(path, "w").write(json_text)


    def load_conversations(self):
        glob_path = glob.glob(join(
            self.dir.user_config_dir,
            '*.conversation.json'
        ))

        for con_path in glob_path:
            name_match = re.findall(r'^.*/(.*)\.conversation\.json$', con_path)

            if name_match:
                data = try_read_json_file(con_path)
                if data:
                    data['name'] = name_match[0]
                    yield data


class State:
    """
    Holds the runtime configuration and chat history.
    It can be loaded from and saved to a JSON files
    """
    def __init__(self, *, storage:Optional[Storage]=None) -> None:
        self.storage = storage if storage else Storage()
        self.settings = self._get_settings()
        self.conversations = self.load_conversations()


    def _get_settings(self):
        settings = self.storage.config

        if settings is None:
            settings = {
                'model_name': 'mistral-nemo:latest',
                'style': 'Blue',
                'context': 'You are being used in a IM style chat program',
                'url': 'http://127.0.0.1:11434',
                'font': 'Arial',
                'font_size': 12
            }

        return filter_dict({
            'context': str,
            'font': str,
            'font_size': int,
            'model_name': str,
            'style': str,
            'url': str,
        }, settings)


    def load_conversations(self):
        conversations = []
        for conversation_dict in self.storage.load_conversations():
            conversations.append(Conversation(**conversation_dict))

        return conversations


    def save(self):
        self.storage.save_all_conversations(self.conversations)
        self.storage.config = self.settings

    def __getitem__(self, key):
        return self.settings[key]


    def __setitem__(self, key, item):
        if key not in self.settings:
            raise KeyError('Key: "%s" not in settings' % key)

        self.settings[key] = item


    def __getitem__(self, key):
        return self.settings[key]