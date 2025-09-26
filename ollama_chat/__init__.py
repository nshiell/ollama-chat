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
#from ollama import chat, list as ai_list, Client
import ollama
import getpass, locale, platform, os
from datetime import datetime
from .state import State
from .style import styles
from .conversation import Conversation

class ModelNames:
    def __init__(self, client, load=False):
        #self._client = client
        self.client = client
        self.models = None
        self.loaded = False
        self.last_exception = None
        #self.bind = Bindings()

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


    #@property
    #def client(self):
    #    return self._client

    #@client.setter
    #def client(self, client):
    #    self._client = client


    def load(self):
        if not self.loaded:
            if self.client is None:
                self.last_exception = 'No client'
                self.loaded = True
                self.models = None
                return

            self.last_exception = None
            try:
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


class QueryThread(QThread):
    word = pyqtSignal(str)
    typing = pyqtSignal(bool)


    def __init__(self, messages, client=None, model_name=None):
        super().__init__()
        self.messages = messages
        self.model_name = model_name
        self.client = client


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
            'model': self.model_name,
            'messages': messages_context + self.messages,
            'stream': True
        }

        for part in self.client.chat(**query):
            self.word.emit(part['message']['content'])

        self.typing.emit(False)


def ask(q_input, thread, conversation, combo_models):
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
    thread.client = conversation.client
    thread.start()


class QScrollAreaChat(QScrollArea):
    def __init__(self):
        super().__init__()

        self.at_bottom = True  # Assume initially at bottom
        self.bind()


    def bind(self):
        vscroll = self.verticalScrollBar()
        vscroll.rangeChanged.connect(self.scroll_to_bottom_if_needed)
        vscroll.valueChanged.connect(self.store_at_bottom_state)


    def store_at_bottom_state(self, value):
        min_snap = self.verticalScrollBar().maximum() - 10
        self.at_bottom = value >= min_snap


    def scroll_to_bottom_if_needed(self, minimum, maximum):
        if self.at_bottom:
            self.verticalScrollBar().setValue(maximum)


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

        try:
            client = ollama.Client(self.state.url)
        except Exception:
            client = None

        self.models = ModelNames(client, True)
        self.conversation.client = self.models.client

        super().__init__()
        self.load_xml('main_window.ui')

        self.setup_thread()

        self.swap_widgets()
        self.setup_remove_template_widgets()
        self.settings_dialog = SettingsDialog(self.state)

        self.message.setFocus()
        self.bind()


    def swap_widgets(self):
        self.swap_widget(self.combo_models, QComboBoxModels(self.models))
        self.swap_widget_deep_clone(self.scrollArea, QScrollAreaChat())


    def word_add(self, word):
        self.current_bubble_text.setText(self.current_bubble_text.text() + word)


    def setup_thread(self):
        self.queryThread = QueryThread(self.conversation.messages)
        self.queryThread.word.connect(self.conversation.add_word)
        self.queryThread.typing.connect(self.conversation.set_assistant_typing)


    def setup_remove_template_widgets(self):
        self.w['frame_assistant'].setParent(None)
        self.w['frame_user'].setParent(None)


    def bind(self):
        self.state.bind('changed', self.state_change)

        self.conversation.bind = {
            'add_word': [self.word_add],
            'assistant_typing': [self.assistant_typing_toggled],
            'add_user_message': [self.add_user_bubble],
        }

        self.message.returnPressed.connect(lambda: ask(
            self.message,
            self.queryThread,
            self.conversation,
            self.combo_models
        ))

        self.send.clicked.connect(lambda: ask(
            self.message,
            self.queryThread,
            self.conversation,
            self.combo_models
        ))

        self.menu('action_configure', self.settings_dialog.show)


    def state_change(self):
        self.models.client = self.create_client(self.state.url)
        self.conversation.client = self.models.client
        self.models.reload()
        self.combo_models.redraw()


    def create_client(self, url):
        try:
            return ollama.Client(url)
        except Exception:
            return None


    def assistant_typing_toggled(self, value):
        if value:
            self.add_assistant_bubble('AI')


    def add_assistant_bubble(self, title, message=None):
        frame = self.clone_widget_into('frame_assistant', QFrame())
        frame.findChild(QLabel, 'author_assistant').setText(title)

        self.current_bubble_text = frame.findChild(QLabel, 'assistant_text')
        self.current_bubble_text.setText(message if message else '')

        self.w['vertical_layout_conversation'].addWidget(frame)
        return frame


    def add_user_bubble(self, message):
        frame = self.clone_widget_into('frame_user', QFrame())

        frame.findChild(QLabel, 'author_user').setText(getpass.getuser())
        frame.findChild(QLabel, 'user_text').setText(message)

        self.w['vertical_layout_conversation'].addWidget(frame)
        return frame


class QComboBoxModels(QComboBox):
    unable_to_connect_text = 'Unable to connect!'

    def __init__(self, models):
        self.models = models
        super().__init__()

        self.redraw(False)

        #models.bind('udpated', self.redraw)

    def redraw(self, clear=True):
        if clear:
            self.clear()

        if self.models.last_exception:
            self.addItems([self.unable_to_connect_text])
            self.setEnabled(False)
        else:
            self.addItems(self.models)
            self.setEnabled(True)


class SettingsDialog(QDialog, WindowMixin):
    def __init__(self, state):
        super().__init__()
        self.load_xml('settings.ui')
        self.state = state

        self.models = ModelNames(self.create_client(self.state.url), True)
        self.bind()
        #self.models.bind('client_change', lambda: print('sdfg'))


    def create_client(self, url):
        try:
            return ollama.Client(url)
        except Exception:
            return None


    def setup_data_state(self):
        self.tabs.setCurrentIndex(0)
        self.swap_widget(self.combo_models, QComboBoxModels(self.models))

        self.plain_text_context.setPlainText(self.state.context)
        self.line_edit_url.setText(self.state.url)

        for i, style_details in enumerate(style.styles):
            self.combo_styles.insertItem(i, style_details.name)
            if style_details.name == self.state.style:
                self.combo_styles.setCurrentIndex(i)

        self.combo_font.setCurrentFont(QFont(self.state.font))
        self.spin_box_font_size.setValue(self.state.font_size)
        self.label_connected.setText('Connected')


    def bind(self):
        self.button_connect.clicked.connect(self.connect)
        self.button_box.accepted.connect(self.ok)
        self.button_box.rejected.connect(self.hide)


    def show(self):
        self.setup_data_state()
        super().show()


    def connect(self):
        self.models.client = self.create_client(self.line_edit_url.text())
        self.models.reload()
        #enable = self.models.client is None
        self.combo_models.redraw()


    def ok(self):
        self.state.update({
            'model_name'    : self.combo_models.currentText(),
            'context'       : self.plain_text_context.toPlainText(),
            'url'           : self.line_edit_url.text(),
            'style'         : self.combo_styles.currentText(),
            'font'          : self.combo_font.currentFont().family(),
            'font_size'     : self.spin_box_font_size.value()
        })
        self.hide()
