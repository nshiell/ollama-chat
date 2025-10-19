import uuid
from .bindings import Bindings

class Conversation:
    def __init__(
            self,
            messages,
            model_name,
            name=None
        ):
        self.mark_for_deletion = False
        self.messages = messages
        self.assistant_typing_ = False
        self.bind = Bindings([
            'word_error',
            'add_word',
            'assistant_typing',
            'add_user_message'
        ])
        self.model_name = model_name
        self.name = name if name else str(uuid.uuid4())
        self.window = None

    def __getattr__(self, method):
        return getattr(self.messages, method)


    def __len__(self):
        return len(self.messages)


    def __getitem__(self, item):
        return self.messages[item]


    def add_word(self, word):
        if not self.messages or self.messages[-1]['role'] != 'assistant':
            self.add_assistant_message()

        self.messages[-1]['content']+= word
        self.bind.trigger('add_word', word)


    @property
    def assistant_typing(self):
        return self.assistant_typing_


    @assistant_typing.setter
    def assistant_typing(self, value):
        self.assistant_typing_ = value
        self.bind.trigger('assistant_typing', value)


    def add_user_message(self, content):
        if self.assistant_typing:
            raise RuntimeError(
                'Unable to add a message while the assistant is typing'
            )

        self.messages.append({'role': 'user', 'content': content})
        self.bind.trigger('add_user_message', content)


    def add_assistant_message(self, content=''):
        self.messages.append({'role': 'assistant', 'content': content})


    def __iter__(self):
        yield 'messages', self.messages
        yield 'model_name', self.model_name