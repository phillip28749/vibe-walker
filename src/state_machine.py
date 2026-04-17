from enum import Enum, auto
from PyQt5.QtCore import QObject, pyqtSignal


class State(Enum):
    """Character states"""
    HIDDEN = auto()
    IDLE = auto()
    WALKING = auto()
    DRAGGED = auto()
    DROPPING = auto()


class StateMachine(QObject):
    """Manages character state transitions"""

    state_changed = pyqtSignal(State)

    def __init__(self):
        super().__init__()
        self._current_state = State.HIDDEN

    @property
    def current_state(self):
        return self._current_state

    def transition_to(self, new_state):
        """Transition to a new state"""
        if new_state == self._current_state:
            return

        self._current_state = new_state
        self.state_changed.emit(new_state)
