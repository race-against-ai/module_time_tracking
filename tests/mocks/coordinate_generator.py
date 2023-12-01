# Copyright (C) 2023, NG:ITL

import json
import pynng

from pathlib import Path
from time import sleep
from time_tracking.utils import read_json

# Constants
CURRENT_DIR = Path(__file__).parent


class CoordinateGenerator:
    def __init__(self):
        self.create_checkpoints()
        self.__pynng_config = read_json(str(CURRENT_DIR.parent.parent / "time_tracking_config.json"))
        self.__checkpoints = None
        self.__generated_coordinates = None
        self.__pub_coordinates = None

        self.define_coordinate_sender()

    def create_checkpoints(self):
        """
        Saves the checkpoints to the `time_tracking.json` file.

        Input/Output:
        None
        """
        self.__checkpoints = {
            "checkpoints": [
                {"x1": 5, "y1": 5, "x2": 6, "y2": 5},
                {"x1": 3, "y1": 1, "x2": 3, "y2": 2},
                {"x1": 3, "y1": 3, "x2": 3, "y2": 4},
            ]
        }
        with open("time_tracking.json", "w") as f:
            json.dump(self.__checkpoints, f, indent=4)

    def define_coordinate_sender(self):
        self.__pub_coordinates = pynng.Pub0()
        self.__pub_coordinates.listen(self.__pynng_config["pynng"]["subscribers"]["__sub_coordinates"]["address"])

    def generate_coordinates(self):
        self.__generated_coordinates = [
            (5.5, 4),
            (5.5, 6),
            (4, 1.5),
            (2, 1.5),
            (4, 3.5),
            (2, 3.5),
            (5.0, 4),
            (5.0, 6),
            (4, 1.0),
            (2, 2.5),
            (4, 4.5),
            (2, 2.5),
            (5.2, 4),
            (5.8, 6),
        ]
        return self.__generated_coordinates

    def send_coordinates(self, p_payload):
        str_with_topic = (
            self.__pynng_config["pynng"]["subscribers"]["__sub_coordinates"]["topics"]["pixel_coordinates"]
            + " "
            + json.dumps(p_payload)
        )
        self.__pub_coordinates.send(str_with_topic.encode("utf-8"))
