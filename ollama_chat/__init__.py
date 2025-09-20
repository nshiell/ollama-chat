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
from .window_mixin import WindowMixin
from ollama import chat, list as ai_list
import getpass, locale, platform, os
from datetime import datetime
from .state import State
from .style import styles


def ai_models():
    class FakeModel:
        def __init__(self, model):
            self.model = model

    try:
        return ai_list().models
    except ConnectionError:
        return [FakeModel('Unable to connect')]


class Conversation:
    def __init__(
            self,
            messages=[],
            assistant_typing=False,
            bind={},
            model_name=None
        ):
        self.messages = messages
        self.assistant_typing_ = assistant_typing
        self.bind = bind
        self.model_name = model_name


    def __getattr__(self, method):
        return getattr(self.messages, method)


    def __len__(self):
        return len(self.messages)


    def __getitem__(self, item):
        return self.messages[item]


    def add_word(self, word):
        if not self.messages or self.messages[-1]['role'] == 'assistant':
            self.add_assistant_message()

        self.messages[-1]['content']+= word
        if 'add_word' in self.bind:
            [cmd(word) for cmd in self.bind['add_word']]


    @property
    def assistant_typing(self):
        return self.assistant_typing_


    @assistant_typing.setter
    def assistant_typing(self, value):
        self.assistant_typing_ = value
        if 'assistant_typing' in self.bind:
            [cmd(value) for cmd in self.bind['assistant_typing']]


    def set_assistant_typing(self, value):
        self.assistant_typing = value


    def add_user_message(self, content):
        if self.assistant_typing:
            raise RuntimeError(
                'Unable to add a message while the assistant is typing'
            )

        self.messages.append({
            'role': 'user',
            'content': content
        })

        if 'add_user_message' in self.bind:
            [cmd(content) for cmd in self.bind['add_user_message']]


    def add_assistant_message(self, content=''):
        self.messages.append({
            'role': 'assistant',
            'content': content
        })


class QueryThread(QThread):
    word = pyqtSignal(str)
    typing = pyqtSignal(bool)


    def __init__(self, messages, model_name=None):
        super().__init__()
        self.messages = messages
        self.model_name = model_name


    def run(self):
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
            'model': 'mistral-nemo',
            'messages': messages_context + self.messages,
            'stream': True
        }

        for part in chat(**query):
            self.word.emit(part['message']['content'])

        self.typing.emit(False)


def ask(q_input, thread, conversation, model_name):
    print(model_name)
    if conversation.assistant_typing:
        return None

    conversation.ai_responding = True

    message = q_input.text().strip()
    if not message:
        return None

    conversation.add_user_message(message)
    q_input.setText('')

    # is this good?
    thread.model_name = conversation.model_name
    thread.start()


class MainWindow(QMainWindow, WindowMixin):
    def __init__(self):
        self.conversation = Conversation([
            {'role': 'system', 'content': '''
                You are being used as a desktop conversational AI,
                the software is called "Ollama Chat"'''
            },

            {'role': 'system', 'content': """
                The user's system language is %s,
                take that into accouunt when replying""" % locale.getlocale()[0]
            },

            {'role': 'system', 'content': "The user's username is '%s'" %
                getpass.getuser()
            },

            {'role': 'system', 'content':
                "The user's operating system is '%s (%s)'" % (
                    platform.system(),
                    os.environ.get('DESKTOP_SESSION')
                )
            }
        ])

        self.state = State()
        self.conversation.model_name = 'mistral-nemo:latest'

        self.current_bubble_text = None
        self.scroll_at_bottom = True  # Assume initially at bottom

        super().__init__()
        self.load_xml('main_window.ui')

        self.setup_thread()
        self.setup_data_state()
        self.setup_remove_template_widgets()

        self.message.setFocus()
        self.bind()


    def setup_data_state(self):
        for i, model in enumerate(ai_models()):
            self.combo_models.insertItem(i, model.model)
            if model.model == self.conversation.model_name:
                self.combo_models.setCurrentIndex(i)


    def word_add(self, word):
        self.current_bubble_text.setText(self.current_bubble_text.text() + word)


    def setup_thread(self):
        self.queryThread = QueryThread(self.conversation.messages)
        self.queryThread.word.connect(self.conversation.add_word)
        self.queryThread.typing.connect(self.conversation.set_assistant_typing)


    def setup_remove_template_widgets(self, ):
        self.frame_assistant.setParent(None)
        self.frame_user.setParent(None)


    def bind(self):
        self.conversation.bind = {
            'add_word': [self.word_add],
            'assistant_typing': [self.assistant_typing_toggled],
            'add_user_message': [self.add_user_bubble],
        }

        self.scrollArea.verticalScrollBar().rangeChanged.connect(
            self.scroll_to_bottom_if_needed
        )

        self.scrollArea.verticalScrollBar().valueChanged.connect(
            self.store_at_bottom_state
        )

        self.message.returnPressed.connect(lambda: ask(
            self.message,
            self.queryThread,
            self.conversation,
            'mistral-nemo'#self.combo_models.currentItem().text()
        ))

        self.send.clicked.connect(lambda: ask(
            self.message,
            self.queryThread,
            self.conversation,
            'mistral-nemo'#self.combo_models.currentItem().text()
        ))

        self.menu('action_configure', self.settings_dialog.show)


    @property
    def settings_dialog(self):
        if not hasattr(self, 'settings_dialog_'):
            self.settings_dialog_ = SettingsDialog(self.state)

        return self.settings_dialog_


    def assistant_typing_toggled(self, value):
        if value:
            self.add_assistant_bubble('AI')


    def add_assistant_bubble(self, title, message=None):
        frame = self.clone_widget_into(self.frame_assistant, QFrame())
        frame.findChild(QLabel, 'author_assistant').setText(title)

        self.current_bubble_text = frame.findChild(QLabel, 'assistant_text')
        self.current_bubble_text.setText(message if message else '')

        self.vertical_layout_conversation.addWidget(frame)
        return frame


    def add_user_bubble(self, message):
        frame = self.clone_widget_into(self.frame_user, QFrame())

        frame.findChild(QLabel, 'author_user').setText(getpass.getuser())
        frame.findChild(QLabel, 'user_text').setText(message)
        self.vertical_layout_conversation.addWidget(frame)
        return frame


    def store_at_bottom_state(self, value):
        min_snap = self.scrollArea.verticalScrollBar().maximum() - 10
        self.scroll_at_bottom = value >= min_snap


    def scroll_to_bottom_if_needed(self, minimum, maximum):
        if self.scroll_at_bottom:
            self.scrollArea.verticalScrollBar().setValue(maximum)


class SettingsDialog(QDialog, WindowMixin):
    def __init__(self, state):
        super().__init__()
        self.load_xml('settings.ui')
        self.state = state
        self.bind()


    def setup_data_state(self):
        self.tabs.setCurrentIndex(0)
        for i, model in enumerate(ai_models()):
            self.combo_models.insertItem(i, model.model)
            if model.model == self.state.default_model:
                self.combo_models.setCurrentIndex(i)

        self.plain_text_context.setPlainText(self.state.context)
        self.line_edit_url.setText(self.state.url)

        for i, style_details in enumerate(style.styles):
            self.combo_styles.insertItem(i, style_details.name)
            if style_details.name == self.state.style:
                self.combo_styles.setCurrentIndex(i)

        self.combo_font.setCurrentFont(QFont(self.state.font))
        self.spin_box_font_size.setValue(self.state.font_size)
        #self.button_connect.connect()


        self.label_connected.setText('Connected')


    def bind(self):
        self.button_box.accepted.connect(self.ok)
        self.button_box.rejected.connect(self.hide)


    def show(self):
        self.setup_data_state()
        super().show()


    def ok(self):
        self.state.default_model = self.combo_models.currentText()
        self.state.context = self.plain_text_context.toPlainText()
        self.state.url = self.line_edit_url.text()
        self.state.style = self.combo_styles.currentText()
        self.state.font = self.combo_font.currentFont().family()
        self.state.font_size = self.spin_box_font_size.value()
        self.hide()
