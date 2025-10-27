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
from .model import *
from .bindings import Bindings

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
    def __init__(self, settings, conversation, models):
        self.conversation = conversation
        self.settings = settings

        self.current_bubble_text = None

        #try:
        #    self.client = ollama.Client(self.settings['url'])
        #except Exception:
            #self.client = None

        self.models = models
        #self.models = ModelNames(self.client, True)

        super().__init__()
        self.load_xml('main_window.ui')

        self.setup_thread()

        self.swap_widgets()
        self.setup_remove_template_widgets()

        # Don't call this on load
        self.settings_dialog = SettingsDialog(self.settings)

        self.message.setFocus()
        self.setup_bindings()


        for message in conversation.messages:
            if message['role'] == 'user':
                self.add_user_bubble(message['content'])
            elif message['role'] == 'assistant':
                self.add_assistant_bubble('AI', message['content'])


    def swap_widgets(self):
        self.swap_widget(
            self.combo_models,
            QComboBoxModels(self.models, self.conversation.model_name)
        )
        self.swap_widget_deep_clone(self.scrollArea, QScrollAreaChat())


    def word_add(self, word):
        self.current_bubble_text.setText(self.current_bubble_text.text() + word)


    def setup_thread(self):
        self.queryThread = QueryThread(self.conversation.messages)
        self.queryThread.word.connect(self.conversation.add_word)

        def set_assistant_typing(value):
            self.conversation.assistant_typing = value
        self.queryThread.typing.connect(set_assistant_typing)


    def setup_remove_template_widgets(self):
        self.w['frame_assistant'].setParent(None)
        self.w['frame_user'].setParent(None)


    def ask(self):
        ask(
            self.message,
            self.queryThread,
            self.conversation,
            self.models.client,
            self.combo_models
        )


    def setup_bindings(self):
        self.bind = Bindings(['new_window_request'])
        self.settings.bind('changed', self.settings_change)
        # fixme!
        self.conversation.bind('add_word', self.word_add)
        self.conversation.bind(
            'assistant_typing',
            self.assistant_typing_toggled
        )
        self.conversation.bind('add_user_message', self.add_user_bubble)

        self.message.returnPressed.connect(self.ask)
        self.send.clicked.connect(self.ask)

        self.menu('action_configure', self.settings_dialog.show)
        self.menu('action_new_window', lambda:
            self.bind.trigger('new_window_request')
        )
        self.menu('action_close_window', self.close)
        self.menu('action_quit', QApplication.quit)


    def closeEvent(self, event):
        result = QMessageBox.question(
            self,
            'Close Conversation',
            'Do you want to close and remove this conversation?',
            QMessageBox.Cancel | QMessageBox.Yes | QMessageBox.No
        )

        if result == QMessageBox.No:
            event.accept()
        elif result == QMessageBox.Yes:
            self.conversation.mark_for_deletion = True
            event.accept()
        else:
            event.ignore()


    def settings_change(self):
        self.models.client = self.create_client(self.settings_dialog.line_edit_url)
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
        else:
            self.current_bubble_frame.done()


    def add_assistant_bubble(self, title, message=None):
        frame = QFrameAssistant(title, message, self.queryThread)
        self.current_bubble_text = frame.current_bubble_text
        self.current_bubble_frame = frame

        self.w['vertical_layout_conversation'].addWidget(frame)
        return frame


    def add_user_bubble(self, message):
        frame = self.clone_widget_into('frame_user', QFrame())

        frame.findChild(QLabel, 'author_user').setText(getpass.getuser())
        frame.findChild(QLabel, 'user_text').setText(message)

        self.w['vertical_layout_conversation'].addWidget(frame)
        return frame


class QFrameAssistant(QFrame):
    def __init__(self, title, message=None, queryThread=None):
        super().__init__()
        self.queryThread = queryThread

        self.populate_widgets()
        self.findChild(QLabel, 'author_assistant').setText(title)
        self.current_bubble_text = self.findChild(QLabel, 'assistant_text')
        self.current_bubble_text.setText(message if message else '')

        if message:
            self.done()

        self.bind()


    def populate_widgets(self):
        class Mixin(QMainWindow, WindowMixin):
            pass
        mixin = Mixin()
        mixin.load_xml('main_window.ui')
        mixin.clone_widget_into('frame_assistant', self)


    def bind(self):
        self.btn_stop.clicked.connect(self.stop)


    def stop(self):
        self.queryThread.stop = True


    def done(self):
        self.btn_stop.setParent(None)
        self.queryThread = None


class QComboBoxModels(QComboBox):
    unable_to_connect_text = 'Unable to connect!'

    def __init__(self, models, selected_model=None):
        self.models = models
        super().__init__()
        self.redraw(False, selected_model)


    def redraw(self, clear=True, selected_model=None):
        if clear:
            self.clear()

        if self.models.last_exception:
            self.addItems([self.unable_to_connect_text])
            self.setEnabled(False)
        else:
            self.addItems(self.models)
            self.setEnabled(True)
            if selected_model in self.models:
                self.setCurrentIndex(self.models.index(selected_model))


class SettingsDialog(QDialog, WindowMixin):
    def __init__(self, settings):
        super().__init__()
        self.load_xml('settings.ui')
        self.settings = settings

        self.models = ModelNames(self.create_client(self.settings['url']), True)
        self.bind()


    def create_client(self, url):
        try:
            return ollama.Client(url)
        except Exception:
            return None


    def setup_data_state(self):
        self.tabs.setCurrentIndex(0)
        self.swap_widget(self.combo_models, QComboBoxModels(self.models))

        self.plain_text_context.setPlainText(self.settings['context'])
        self.line_edit_url.setText(self.settings['url'])

        #for i, style_details in enumerate(self.settings.style.styles):
        #    self.combo_styles.insertItem(i, style_details.name)
        #    if style_details.name == self.settings['style']:
        #        self.combo_styles.setCurrentIndex(i)

        self.combo_font.setCurrentFont(QFont(self.settings['font']))
        self.spin_box_font_size.setValue(self.settings['font_size'])
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
        self.combo_models.redraw()


    def ok(self):
        self.settings.update(
            model_name=self.combo_models.currentText(),
            context=self.plain_text_context.toPlainText(),
            url=self.line_edit_url.text(),
            style=self.combo_styles.currentText(),
            font=self.combo_font.currentFont().family(),
            font_size=self.spin_box_font_size.value()
        )
        self.hide()
