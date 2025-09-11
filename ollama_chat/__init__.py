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


messages = []
latest_repsonse_message = ''
ai_responding = False


class QueryThread(QThread):
    word = pyqtSignal(str)
    done = pyqtSignal(bool)


    def __init__(self, messages):
        super().__init__()
        self.messages = messages


    def run(self):
        print(messages)
        print('=-=-=--')
        for part in chat(model='mistral-nemo', messages=messages, stream=True):
            self.word.emit(part['message']['content'])

        self.done.emit(True)


def ask(q_input, thread, add_user_bubble, add_assistant_bubble):
    global messages
    global ai_responding
    global latest_repsonse_message
    
    if ai_responding:
        return None
    
    ai_responding = True
        
    message = q_input.text().strip()
    if not message:
        return None

    add_user_bubble('bob', message)
    add_assistant_bubble('stuff')


    if latest_repsonse_message:
        messages.append({'role': 'assistant', 'content': latest_repsonse_message})
        latest_repsonse_message = ''

    messages.append({'role': 'user', 'content': message})
    q_input.setText('')
    thread.start()


class MainWindow(QMainWindow, WindowMixin):
    def word_add(self, word):
        global latest_repsonse_message
        latest_repsonse_message += word
        self.current_bubble.setText(latest_repsonse_message)


    def word_done(self):
        global ai_responding
        ai_responding = False


    def __init__(self):
        global messages
        
        super().__init__()
        self.load_xml('main_window.ui')

        self.message.setFocus()

        self.queryThread = QueryThread(messages)
        self.queryThread.word.connect(self.word_add)
        self.queryThread.done.connect(self.word_done)

        self.scroll_at_bottom = True  # Assume initially at bottom
        
        self.frame_assistant.setParent(None)
        self.frame_user.setParent(None)
        
        self.bind()

        self.current_bubble = None



    def bind(self):
        self.scrollArea.verticalScrollBar().rangeChanged.connect(
            self.scroll_to_bottom_if_needed
        )

        self.scrollArea.verticalScrollBar().valueChanged.connect(
            self.store_at_bottom_state
        )

        self.message.returnPressed.connect(lambda: ask(
            self.message,
            self.queryThread,
            self.add_user_bubble,
            self.add_assistant_bubble
        ))

        self.send.clicked.connect(lambda: ask(
            self.message,
            self.queryThread,
            self.add_user_bubble,
            self.add_assistant_bubble
        ))

    
    
    def add_assistant_bubble(self, title, message=None):
        frame = self.clone_widget_into(self.frame_assistant, QFrame())
        frame.findChild(QLabel, 'author_assistant').setText(title)
        
        self.current_bubble = frame.findChild(QLabel, 'assistant_text')
        
        if message:
            self.current_bubble.setText(message)
        
        self.verticalLayout_4.addWidget(frame)
        return frame
    
    
    def add_user_bubble(self, title, message):
        frame = self.clone_widget_into(self.frame_user, QFrame())
        print(frame)
        frame.findChild(QLabel, 'author_user').setText(title)
        frame.findChild(QLabel, 'user_text').setText(message)
        self.verticalLayout_4.addWidget(frame)
        return frame
    

    def store_at_bottom_state(self, value):
        min_snap = self.scrollArea.verticalScrollBar().maximum() - 10
        self.scroll_at_bottom = value >= min_snap


    def scroll_to_bottom_if_needed(self, minimum, maximum):
        if self.scroll_at_bottom:
            self.scrollArea.verticalScrollBar().setValue(maximum)
    
