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

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QWidget
from .conversation import Conversation
import getpass, locale, platform, os
import ollama
from datetime import datetime
from abc import ABC, abstractmethod


class QueryThread(QThread):
    word = pyqtSignal(str)
    typing = pyqtSignal(bool)
    word_error = pyqtSignal(str)


    def __init__(self,
            messages,
            client=None,model_name=None,
            context:Optional[str]=None):
        super().__init__()
        self.messages = messages
        self.model_name = model_name
        self.client = client
        self.stop = False
        self.context = context


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

        if self.context:
            messages_context.append({'role': 'system', 'content': self.context})

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



class AskerAbstract(ABC):
    """
    For wrapping around the thread
    For handling the inout and initiating the query
    """

    def __init__(self, *,
            conversation : Conversation,
            client_wrapper,
            context:Optional[str]=None) -> None: # add in a type

        self.conversation = conversation
        self.client_wrapper = client_wrapper
        self.context = context

        # If self.thread is None, then we are NOT tyring a reply from the AI
        self.thread: Optional[QueryThread] = None


    def _prepair_message(self, message: str) -> str:
        """
        Does processing on the inout string before sending the message
        """
        return message.strip()


    def _create_thread(self, model_name) -> None:
        """
        Create a new QueryThread() in self.thread
        """

        self.thread = QueryThread(
            self.conversation.messages,
            self.client_wrapper.client,
            model_name,
            self.context
        )


    @abstractmethod
    def ask(self) -> None:
        """
        Start answering the current message
        """
        pass


def create_client(url):
    try:
        return ollama.Client(host=url, timeout=3)
    except Exception:
        return None