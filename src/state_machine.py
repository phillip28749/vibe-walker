from enum import Enum, auto
from PyQt5.QtCore import QObject, pyqtSignal


class State(Enum):
    """Character states"""
    HIDDEN = auto()
    IDLE = auto()
    WALKING = auto()
    DRAGGED = auto()
    DROPPING = auto()
    WAVING = auto()
    APPEARING = auto()


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
        """Transition to a new state

        Args:
            new_state: State enum member to transition to

        Raises:
            TypeError: If new_state is not a State enum member
        """
        if not isinstance(new_state, State):
            raise TypeError(f"new_state must be a State enum, got {type(new_state).__name__}")

        if new_state == self._current_state:
            return

        self._current_state = new_state
        self.state_changed.emit(new_state)
