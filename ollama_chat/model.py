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
from PyQt5.QtCore import QThread, pyqtSignal
import getpass, locale, platform, os
import ollama

#from .widgets import *


class QueryThread(QThread):
    word = pyqtSignal(str)
    typing = pyqtSignal(bool)
    word_error = pyqtSignal(str)


    def __init__(self, messages, client=None, model_name=None):
        super().__init__()
        self.messages = messages
        self.model_name = model_name
        self.client = client
        self.stop = False


    def run(self):
        self.stop = False
        self.typing.emit(True)

        messages_context = [
            {'role': 'system', 'content':
                "The current date/time is '%s'" % datetime.now()
            },
            {'role': 'system', 'content':
                "The current user's username is '%s'" % getpass.getuser()
            }
        ]

        query = {
            'model': self.model_name,
            'messages': messages_context + self.messages,
            'stream': True
        }

        for part in self.client.chat(**query):
            try:
                self.word.emit(part['message']['content'])
            except ResponseError as e:
                self.word_error.emit(e)

            if self.stop:
                break

        self.typing.emit(False)


class ModelNames:
    def __init__(self, client, load=False):
        self.client = client
        self.models = None
        self.loaded = False
        self.last_exception = None

        if load:
            self.load()


    def __getattr__(self, method):
        self.load()
        if self.models is None:
            return None
        return getattr(self.models, method)


    def __len__(self):
        self.load()
        if self.models is None:
            return 0
        return len(self.models)


    def __iter__(self):
        self.load()
        if self.models is None:
            return iter([])
        return iter(self.models)


    def __getitem__(self, item):
        self.load()
        if self.models is None:
            return None
        return self.models[item]


    def load(self):
        if not self.loaded:
            if self.client is None:
                self.last_exception = 'No client'
                self.loaded = True
                self.models = None
                return

            self.last_exception = None
            try:
                # blocking if there is no connection!
                self.models = [m.model for m in self.client.list().models]
            except Exception as e:
                self.models = None
                self.loaded = True
                self.last_exception = e
                return

        self.loaded = True
        self.last_exception = None


    def reload(self):
        self.loaded = False
        self.load()


def ask(q_input, thread, conversation, client, combo_models):
    if conversation.assistant_typing:
        return None

    conversation.ai_responding = True
    conversation.model_name = combo_models.currentText()

    message = q_input.text().strip()
    if not message:
        return None

    conversation.add_user_message(message)
    q_input.setText('')

    # is this good?
    thread.model_name = conversation.model_name
    thread.client = client
    thread.start()


def create_client(url):
    try:
        return ollama.Client(url)
    except Exception:
        return None