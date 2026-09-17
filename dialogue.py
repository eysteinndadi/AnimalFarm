class DialogueSession:
    """A paged conversation: E advances, ends after the last line."""

    def __init__(self, speaker, lines):
        self.speaker = speaker
        self.lines = list(lines)
        self.index = 0

    @property
    def current_line(self):
        return self.lines[self.index]

    @property
    def done(self):
        return self.index >= len(self.lines)

    def advance(self):
        self.index += 1
