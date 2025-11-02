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
from .window_mixin import WindowMixin
from .model import *
from .conversation import Conversation
from .bindings import Bindings
from typing import Optional
from ollama import Client
from .asker import *

class ScrollAreaChat(QScrollArea):
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
    """
    The window for conducting chats
    """

    def __init__(self, *,
            settings     : Settings,
            conversation : Conversation,
            models       : ModelNames) -> None:

        self.conversation = conversation
        self.settings = settings

        self.current_bubble_text = None

        self.models = models

        super().__init__()
        self.load_xml('main_window.ui')

        self.swap_widgets()
        self.setup_remove_template_widgets()

        self.ask = Asker(
            q_message=self.message,
            conversation=conversation,
            context=settings['context'],
            client_wrapper=self.models,
            q_combo_models=self.combo_models
        )

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
            ComboBoxModels(self.models, self.conversation.model_name)
        )
        self.swap_widget_deep_clone(self.scrollArea, ScrollAreaChat())


    def word_add(self, word):
        self.current_bubble_text.setText(self.current_bubble_text.text() + word)


    def setup_remove_template_widgets(self):
        self.w['frame_assistant'].setParent(None)
        self.w['frame_user'].setParent(None)


    def setup_bindings(self):
        self.bind = Bindings(['new_window_request', 'settings_show_request'])

        # fixme!
        self.conversation.bind('add_word', self.word_add)
        self.conversation.bind(
            'assistant_typing',
            self.assistant_typing_toggled
        )
        self.conversation.bind('add_user_message', self.add_user_bubble)

        self.message.returnPressed.connect(self.ask)
        self.send.clicked.connect(self.ask)

        self.menu('action_configure', lambda:
            self.bind.trigger('settings_show_request')
        )
        #self.menu('action_configure', self.settings_dialog.show)
        self.menu('action_new_window', lambda:
            self.bind.trigger('new_window_request')
        )
        self.menu('action_close_window', self.close)
        self.menu('action_quit', QApplication.quit)


    def closeEvent(self, event):
        result = QMessageBox.question(
            self,
            'Close Conversation',
            '''Do you want o discard this conversation?
Do you want to close the program?''',
            QMessageBox.No | QMessageBox.Cancel | QMessageBox.Close | QMessageBox.Discard
        )

        if result == QMessageBox.No:
            event.accept()
        elif result == QMessageBox.Close:
            event.accept()
            QApplication.quit()
        elif result == QMessageBox.Discard:
            self.conversation.mark_for_deletion = True
            event.accept()
        else:
            event.ignore()


    def settings_changed(self):
        self.ask.context = self.settings['context']
        #todo fixme!


    def assistant_typing_toggled(self, value):
        if value:
            self.add_assistant_bubble('AI')
        else:
            self.current_bubble_frame.done()


    def add_assistant_bubble(self, title, message=None):
        frame = FrameAssistant(title, message, self.ask.thread)
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


class FrameAssistant(QFrame):
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


class ComboBoxModels(QComboBox):
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
        self.setup_bindings()


    def setup_data_state(self):
        self.models = ModelNames(create_client(self.settings['url']), True)
        self.tabs.setCurrentIndex(0)
        self.swap_widget(self.combo_models, ComboBoxModels(self.models))

        self.plain_text_context.setPlainText(self.settings['context'])
        self.line_edit_url.setText(self.settings['url'])

        #for i, style_details in enumerate(self.settings.style.styles):
        #    self.combo_styles.insertItem(i, style_details.name)
        #    if style_details.name == self.settings['style']:
        #        self.combo_styles.setCurrentIndex(i)

        self.combo_font.setCurrentFont(QFont(self.settings['font']))
        self.spin_box_font_size.setValue(self.settings['font_size'])
        self.label_connected.setText('Connected')


    def setup_bindings(self):
        self.bind = Bindings(['settings_changed', 'client_change_request'])

        self.button_connect.clicked.connect(self.connect)
        self.button_box.accepted.connect(self.ok)
        self.button_box.rejected.connect(self.hide)


    def show(self):
        self.setup_data_state()
        super().show()


    def connect(self):
        self.models.client = create_client(self.line_edit_url.text())
        self.models.reload()
        self.combo_models.redraw()


    def ok(self):
        new_url = self.line_edit_url.text()
        if self._check_values_changed(True):
            self.bind.trigger('client_change_request', new_url)

        # Need to do this before overwriting values
        values_changed = self._check_values_changed()

        self.settings['model_name'] = self.combo_models.currentText()
        self.settings['context'] = self.plain_text_context.toPlainText()
        self.settings['url'] = self.line_edit_url.text()
        self.settings['style'] = self.combo_styles.currentText()
        self.settings['font'] = self.combo_font.currentFont().family()
        self.settings['font_size'] = self.spin_box_font_size.value()

        if values_changed:
            self.bind.trigger('settings_changed')

        self.hide()


    def _check_values_changed(self, url_only:bool=False) -> bool:
        if self.settings['url'] != self.line_edit_url.text():
            return True

        if url_only:
            return False

        if self.settings['model_name'] != self.combo_models.currentText():
            return True
        if self.settings['context'] != self.plain_text_context.toPlainText():
            return True
        #if self.settings['style'] != self.combo_styles.currentText():
        #    return True
        if self.settings['font'] != self.combo_font.currentFont().family():
            return True
        if self.settings['font_size'] != self.spin_box_font_size.value():
            return True

        return False