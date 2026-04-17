import pytest
from src.state_machine import State, StateMachine


def test_state_enum_values():
    """Test all 5 states exist"""
    assert State.HIDDEN is not None
    assert State.IDLE is not None
    assert State.WALKING is not None
    assert State.DRAGGED is not None
    assert State.DROPPING is not None


def test_initial_state_is_hidden():
    """State machine starts in HIDDEN state"""
    sm = StateMachine()
    assert sm.current_state == State.HIDDEN


def test_transition_to_idle():
    """Can transition from HIDDEN to IDLE"""
    sm = StateMachine()
    sm.transition_to(State.IDLE)
    assert sm.current_state == State.IDLE


def test_transition_emits_signal(qtbot):
    """State change emits signal"""
    sm = StateMachine()
    with qtbot.waitSignal(sm.state_changed) as blocker:
        sm.transition_to(State.IDLE)
    assert blocker.args[0] == State.IDLE


def test_no_signal_on_same_state(qtbot):
    """No signal when transitioning to current state"""
    sm = StateMachine()
    sm.transition_to(State.IDLE)

    # Should not emit signal
    with qtbot.assertNotEmitted(sm.state_changed):
        sm.transition_to(State.IDLE)
