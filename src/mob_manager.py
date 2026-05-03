"""Creates extra companion mobs for concurrent activity sources."""

from PyQt5.QtCore import QObject, QTimer

from src.companion_window import CompanionWindow


class MobManager(QObject):
    """Keeps companion mobs in sync with the active instance count."""

    def __init__(self, config, activity_monitor):
        super().__init__()
        self.config = config
        self.activity_monitor = activity_monitor
        self.active_instance_count = 0
        self.companion_windows = []

        self.activity_monitor.active_instance_count_changed.connect(self.on_active_instance_count_changed)

        # Reconcile periodically so config-driven mode changes are reflected too.
        self.reconcile_timer = QTimer(self)
        self.reconcile_timer.timeout.connect(self._reconcile_companions)
        self.reconcile_timer.start(500)

    def on_active_instance_count_changed(self, count):
        """Update companion count when monitored activity changes."""
        self.active_instance_count = count
        self._reconcile_companions()

    def on_reactive_mode_changed(self, enabled):
        """Refresh companions when reactive mode is toggled."""
        self._reconcile_companions()

    def _target_companion_count(self):
        """Return how many extra mobs should be visible."""
        if not self.config.reactive_mode_enabled:
            return 0
        if self.config.behavior_mode != "vibe":
            return 0
        return max(0, self.active_instance_count - 1)

    def _reconcile_companions(self):
        """Create or remove companions until the target count is met."""
        target_count = self._target_companion_count()
        active_companions = [window for window in self.companion_windows if not window.is_fading()]
        fading_companions = [window for window in self.companion_windows if window.is_fading()]

        while fading_companions and len(active_companions) < target_count:
            companion = fading_companions.pop()
            companion.cancel_fade_out()
            active_companions.append(companion)

        while len(active_companions) < target_count:
            companion = CompanionWindow(self.config, slot_index=len(self.companion_windows) + 1)
            companion.window_closed.connect(self._on_companion_closed)
            companion.show()
            self.companion_windows.append(companion)
            active_companions.append(companion)

        while len(active_companions) > target_count:
            companion = active_companions.pop()
            companion.begin_fade_out()

    def _on_companion_closed(self, companion):
        """Remove a companion from tracking after it finishes fading out."""
        if companion in self.companion_windows:
            self.companion_windows.remove(companion)

    def close_all(self):
        """Close every companion mob during shutdown."""
        self.reconcile_timer.stop()
        while self.companion_windows:
            self.companion_windows.pop().close()
