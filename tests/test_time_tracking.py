# Copyright (C) 2023, NG:ITL
from tests.mocks.coordinate_generator import CoordinateGenerator
from time_tracking.time_tracking import LapTimer
from time_tracking import utils
from pathlib import Path
import unittest

# Constants
CURRENT_DIR = Path(__file__).parent


# Reminder: Naming convention for unit tests
#
# test_InitialState_PerformedAction_ExpectedResult


class TimeTrackingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.correct_log = utils.read_json(str(CURRENT_DIR / "time_tracking_output_correct.json"))
        print("Coordinate_generator started")
        self.generator = CoordinateGenerator()
        self.coordinates = self.generator.generate_coordinates()
        print("Checkpoints and coordinates created")
        self.timer = LapTimer(test=True)
        self.timer.start_timer()
        print("Timer started")

    def tearDown(self) -> None:
        pass

    def test_timeTracking_Run_CorrectOutput(self) -> None:
        for coordinate in self.coordinates:
            self.generator.send_coordinates(coordinate)
            self.timer.run()

        self.log = utils.read_json(str(CURRENT_DIR.parent / "time_tracking_output.json"))
        if self.correct_log == self.log:
            print("yes")
            self.assertTrue(True)
        else:
            print("nono")
            self.assertTrue(False)
