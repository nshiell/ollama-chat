import uuid

class Conversation:
    def __init__(
            self,
            messages=[],
            model_name=None,
            client=None,
            name=None
        ):
        self.mark_for_deletion = False
        self.messages = messages
        self.assistant_typing_ = False
        self.bind = None
        self.model_name = model_name
        self.client = client
        self.name = name if name else str(uuid.uuid4())


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


    def __iter__(self):
        yield 'messages', self.messages
        yield 'model_name', self.model_name
