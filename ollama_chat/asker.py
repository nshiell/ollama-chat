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
from .model import AskerAbstract


class Asker(AskerAbstract):
    def __init__(self, *,
            conversation   : Conversation,
            client_wrapper : client_wrapper,
            context:Optional[str]=None,
            q_message      : QWidget,
            q_combo_models : QWidget) -> None:

        super().__init__(
            conversation=conversation,
            client_wrapper=client_wrapper,
            context=context
        )

        self.q_message = q_message
        self.q_combo_models = q_combo_models

        self.thread: Optional[QueryThread] = None


    def set_assistant_typing(self, value) -> None:
        self.conversation.assistant_typing = value
        if not value and self.thread:
            self.thread.quit()
            self.thread.wait()
            self.thread = None


    def __call__(self) -> None:
        self.ask()


    def ask(self) -> None:
        """
        Send a new message to the stack and fire up the thread to get the
        API client to answer it
        """
        if self.thread:
            return None

        query_text = self._prepair_message(self.q_message.text())

        if not query_text:
            return None

        self.conversation.add_user_message(query_text)
        self.q_message.setText('')

        self._create_thread(self.q_combo_models.currentText())
        self.thread.word.connect(self.conversation.add_word)
        self.thread.typing.connect(self.set_assistant_typing)
        self.thread.start()