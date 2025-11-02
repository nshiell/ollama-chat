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
    def __init__(self, argv) -> None:
        super().__init__(argv)
        self.state = State()
        self.conversations = self.state.conversations
        self.setup_model_client(self.state['url'])
        self.settings_dialog = self.create_settngs_dialog()


    # make this only be created if needed!
    def create_settngs_dialog(self):
        dialog = SettingsDialog(self.state)
        dialog.bind('client_change_request', self.setup_model_client)
        return dialog


    def setup_model_client(self, url:str):
        self.client = create_client(url)
        self.models = ModelNames(self.client)


    def show_conversation_windows(self) -> None:
        if not len(self.conversations):
            self.add_new_conversation_window()
            return

        for conversation in self.conversations:
            if not conversation.window:
                self.add_window_to_conversation(conversation)


    def add_window_to_conversation(self, conversation:Conversation) -> None:
        win = MainWindow(
            defaultSettings=self.state.settings,
            conversation=conversation,
            models=self.models
        )

        win.bind('new_window_request', self.add_new_conversation_window)
        win.bind('settings_show_request', self.settings_dialog.show)

        self.settings_dialog.bind('settings_changed', win.settings_changed)

        win.show()
        conversation.window = win


    def add_new_conversation_window(self) -> None:
        self.conversations.append(Conversation(
            messages=[],
            model_name=self.state.settings['model_name']
        ))

        self.show_conversation_windows()


    def save_state(self) -> None:
        self.state.save()