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


def test_invalid_state_raises_error():
    """Attempting to transition to invalid state raises TypeError"""
    sm = StateMachine()
    with pytest.raises(TypeError):
        sm.transition_to("INVALID")
    with pytest.raises(TypeError):
        sm.transition_to(None)


def test_multiple_state_transitions(qtbot):
    """Can transition through multiple states sequentially"""
    sm = StateMachine()

    # HIDDEN -> IDLE -> WALKING -> DRAGGED -> DROPPING -> IDLE
    sm.transition_to(State.IDLE)
    assert sm.current_state == State.IDLE

    sm.transition_to(State.WALKING)
    assert sm.current_state == State.WALKING

    sm.transition_to(State.DRAGGED)
    assert sm.current_state == State.DRAGGED

    sm.transition_to(State.DROPPING)
    assert sm.current_state == State.DROPPING

    sm.transition_to(State.IDLE)
    assert sm.current_state == State.IDLE
