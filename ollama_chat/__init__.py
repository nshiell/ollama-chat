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
from ollama import chat
import getpass, locale, platform, os
from datetime import datetime


class Conversation:
    def __init__(self, messages=[], assistant_typing=False, bind={}):
        self.messages = messages
        self.assistant_typing_ = assistant_typing
        self.bind = bind


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


    def __init__(self, messages):
        super().__init__()
        self.messages = messages


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


def ask(q_input, thread, conversation):
    if conversation.assistant_typing:
        return None
    
    conversation.ai_responding = True
        
    message = q_input.text().strip()
    if not message:
        return None

    conversation.add_user_message(message)
    q_input.setText('')
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

        self.current_bubble_text = None
        self.scroll_at_bottom = True  # Assume initially at bottom
        
        super().__init__()
        self.load_xml('main_window.ui')
        
        self.setup_thread()
        self.setup_remove_template_widgets()
        
        self.message.setFocus()
        self.bind()


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
            self.conversation
        ))

        self.send.clicked.connect(lambda: ask(
            self.message,
            self.queryThread,
            self.conversation
        ))

    
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
