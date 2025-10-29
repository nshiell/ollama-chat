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
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from .widgets import *
from .window_mixin import WindowMixin
#from ollama import chat, list as ai_list, Client
#import ollama
import getpass, locale, platform, os

#from .state import State
from .style import styles
from .conversation import Conversation

from .state import State


#from .bindings import Bindings
class QApplicationOllamaChat(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.state = State()
        self.conversations = self.state.conversations
        self.client = create_client(self.state.settings['url'])
        self.models = ModelNames(self.client)


    def show_conversation_windows(self):
        if not len(self.conversations):
            self.add_new_conversation_window()
            return

        for conversation in self.conversations:
            if not conversation.window:
                win = MainWindow(self.state.settings, conversation, self.models)
                win.bind('new_window_request', self.add_new_conversation_window)
                win.show()
                conversation.window = win


    def add_new_conversation_window(self):
        self.conversations.append(Conversation(
            messages=[],
            model_name=self.state.settings['model_name']
        ))

        self.show_conversation_windows()


    def save_state(self):
        self.state.save()