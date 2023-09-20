# Copyright (C) 2023, NG:ITL
import time
import json
import pynng
import cv2
import os
import numpy as np

from pathlib import Path
from threading import Timer


def read_config(config_file_name: str) -> dict:
    """
    Args:
        config_file_name: name of the config file that should be read
    Returns:
        dict
    """
    search_directory_list = [Path(os.getcwd()), Path(os.getcwd()).parent, Path(__file__).parent]
    for directory in search_directory_list:
        filepath = directory / config_file_name
        if filepath.is_file():
            with open(config_file_name, "r") as file:
                return json.load(file)
    print("----!File not found!----")
    return {}


def find_config_file(relative_path: str) -> bool:
    """
    Args:
        relative_path: name of the config file that should be found
    Returns:
        bool
    """
    search_directory_list = [Path(os.getcwd()), Path(os.getcwd()).parent, Path(__file__).parent]
    for directory in search_directory_list:
        filepath = directory / relative_path
        if filepath.is_file():
            print("-----!config file exists!-----")
            return True
    print("-----!File not found!-----")
    return False


def run_scheduled_task(p_time: int, scheduled_task, arg=None) -> None:
    """
    Args:
        p_time: time till the method will be executed
        scheduled_task: method that should be run
        arg: argument that should be passed to the method

    Returns:
        None
    """
    threading_timer = Timer(p_time, scheduled_task, [arg])
    threading_timer.start()


class LapTimer:
    def __init__(self, config_file_path="time_tracking.json", p_fallback: bool = False, test: bool = False):
        # initialise variables
        self.__test = test
        self.coordinates_list: list = []
        self.__start_time: float = 0.0
        self.__last_lap_time: float = 0.0
        self.__last_checkpoint_time: float = 0.0
        self.__checkpoints: list = []
        self.__payload: dict = {}
        self.__checkpoint_drawn = False
        self.__fallback = p_fallback
        self.__video_path = "C:/Users/VWF6GWD/Desktop/Race_against_ai_workspace/TestVideo/drive_990p.h265"
        self.__user: str | None = "anon"

        # getting best times from database interface
        self.__best_times = self.request_best_times()
        self.__pers_best_times = {
            "sector_1_best_time": 1000.0,
            "sector_2_best_time": 1000.0,
            "sector_3_best_time": 1000.0,
            "lap_best_time": 1000.0,
        }

        # getting checkpoint positions from config file
        if find_config_file(config_file_path) is False:
            if self.__test is False:
                self.__definer = CheckpointDefiner()
            else:
                self.__definer = CheckpointDefiner(p_use_camera_stream=False, video_path=self.__video_path)
            self.__definer.main()

        self.__config = read_config(config_file_path)
        self.__number_of_checkpoints = len(self.__config["checkpoints"])
        self.__checkpoint_list = self.__config["checkpoints"]

        self.__pynng_config = read_config("time_tracking_config.json")

        self.__define_coordinate_receiver()
        self.__define_frame_receiver()
        self.__define_user_receiver()

        for i in range(self.__number_of_checkpoints):
            if i == 0:
                self.__checkpoints.append(FinishLineCheckpoint(self.__checkpoint_list[i], self.__number_of_checkpoints))
            else:
                self.__checkpoints.append(SectorLineCheckpoint(self.__checkpoint_list[i], i))

        # setting up a pynng sockets
        self.__pub_time = pynng.Pub0()
        self.__pub_time.listen(self.__pynng_config["pynng"]["publishers"]["__pub_time"]["address"])

        self.__pub_frame = pynng.Pub0()
        self.__pub_frame.listen(self.__pynng_config["pynng"]["publishers"]["__pub_frame"]["address"])

    def start_timer(self) -> None:
        self.__start_time = time.time()
        self.send_lap_start()

    def run(self) -> None:
        """
        main function
        Returns: None
        """
        self.draw()
        self.checkpoint_check()
        self.__user = self.receive_user()
        if self.__user is not None:
            self.change_user(self.__user)

    def checkpoint_check(self) -> None:
        """
        loops through every "checkpoint" and checks if the car went through. When that happens it sets the helper
        variable to True. If the finish line is activated it checks if the lap counts using the crossed variable

        Returns: none
        """
        if self.__fallback is False:
            coordinates = Point(self.receive_coordinates())
            self.coordinates_list.append(coordinates)
            if len(self.coordinates_list) > 2:
                self.coordinates_list.pop(0)
                for checkpoint in self.__checkpoints:
                    if isinstance(checkpoint, FinishLineCheckpoint):  # check if checkpoint is a finish line
                        if checkpoint.check(self.coordinates_list):
                            correct = self.lap_valid()
                            self.checkpoint_update(self.__number_of_checkpoints)
                            self.lap_update(correct)
                    else:
                        if checkpoint.check(self.coordinates_list):
                            self.checkpoint_update(checkpoint.get_num())
        else:
            received_bytes = self.__sub_coordinates.recv()
            num = int.from_bytes(received_bytes, "big")
            self.checkpoint_update(num)
            if num != 3:
                self.__checkpoints[num].set_crossed(True)
            else:
                self.__checkpoints[0].set_crossed(True)
                self.lap_update(self.lap_valid())

    def lap_update(self, correct: bool) -> None:
        """
        calculates the lap time, resets the crossed variables, sending lap data, start new lap(send_lap, lap start)
        Args:
            correct: if the lap was driven correct (car drove through all checkpoints)

        Returns: none

        """
        if self.__last_lap_time != 0:
            lap_time = round(time.time() - self.__last_lap_time, 2)
        else:
            lap_time = round(time.time() - self.__start_time, 2)

        self.__last_lap_time = time.time()

        for checkpoint in self.__checkpoints:
            checkpoint.set_crossed(False)

        self.send_lap(lap_time, correct)
        self.send_lap_start()

    def checkpoint_update(self, n: int) -> None:
        """
        calculate checkpoint times and sends the sector information via pynng(send_sector)
        Args:
            n: sector number

        Returns: none
        """
        if self.__last_checkpoint_time != 0:
            in_lap_time = round((time.time() - self.__last_checkpoint_time), 2)
        else:
            in_lap_time = round(time.time() - self.__start_time, 2)

        self.__last_checkpoint_time = time.time()

        # sending data
        self.send_sector(n, in_lap_time, True)

    def lap_valid(self) -> bool:
        """
        checks if lap is correct (car driven through every section)
        Returns: boolean
        """
        for checkpoint in self.__checkpoints:
            if checkpoint.get_crossed() is False:
                return False
        return True

    def calc_type(self, p_time: float, p_sector: str, p_valid: bool) -> str:
        """
         calculates if the time is an alltime best(purple), personal best(green) or just a normal time(orange)
         changes the alltime and personal best values if necessary
        Args:
            p_time: sector time
            p_sector: which sector
            p_valid: if the sector was driven correct

        Returns: string
        """
        if p_time < self.__best_times[f"{p_sector}_best_time"]:
            if p_valid:
                self.__best_times[f"{p_sector}_best_time"] = p_time
            if p_time < self.__pers_best_times[f"{p_sector}_best_time"]:
                if p_valid:
                    self.__pers_best_times[f"{p_sector}_best_time"] = p_time
            return "purple"
        elif p_time < self.__pers_best_times[f"{p_sector}_best_time"]:
            if p_valid:
                self.__pers_best_times[f"{p_sector}_best_time"] = p_time
            return "green"
        else:
            return "yellow"

    def request_best_times(self) -> dict:
        """
        request all-time best times from the database
        Returns:
            dict
        """
        best_times = {
            "sector_1_best_time": 9.87,
            "sector_2_best_time": 4.08,
            "sector_3_best_time": 5.53,
            "lap_best_time": 19.48,
        }
        return best_times

    def __define_coordinate_receiver(self) -> None:
        """
        defines pynng receiver for the coordinates received from the vehicle tracking component
        Returns:
            None
        """
        if self.__fallback is False:
            self.__sub_coordinates = pynng.Sub0()
            self.__sub_coordinates.subscribe(
                self.__pynng_config["pynng"]["subscribers"]["__sub_coordinates"]["topics"]["pixel_coordinates"]
            )
            self.__sub_coordinates.dial(self.__pynng_config["pynng"]["subscribers"]["__sub_coordinates"]["address"])
        else:
            self.__sub_coordinates = pynng.Sub0()
            self.__sub_coordinates.subscribe("")
            self.__sub_coordinates.dial(
                self.__pynng_config["pynng"]["subscribers"]["__sub_coordinates_fallback"]["address"]
            )

    def receive_coordinates(self) -> tuple:
        """
        receives the coordinates and returns them
        Returns: tuple
        """
        msg = self.__sub_coordinates.recv()
        i = msg.find(" ")
        data = msg[i + 1 :]
        json_data = data.decode("utf-8")
        coordinates = json.loads(json_data)
        return coordinates

    def send_sector(self, p_sector: int, p_time: float, p_valid: bool) -> None:
        """
        is activated when a sector is crossed, prepares the data that should be sent

        Args:
            p_sector: the sector that was crossed
            p_time: the time needed for the sector
            p_valid: if the sector was driven valid

        Returns: None
        """
        self.__payload.clear()
        self.__payload = {
            "current_driver": self.__user,
            "sector_number": p_sector,
            "sector_time": p_time,
            "sector_valid": p_valid,
            "type": self.calc_type(p_time, f"sector_{p_sector}", True),
        }
        msg = self.__payload
        self.send_data(msg, self.__pynng_config["pynng"]["publishers"]["__pub_time"]["topics"]["sector:finished"])

    def send_lap(self, p_time: float, p_valid: bool) -> None:
        """
        is activated when a lap is finished, prepares the data that should be sent

        Args:
            p_time: the time needed for the lap
            p_valid: if the lap was driven valid

        Returns: None
        """
        self.__payload.clear()
        self.__payload = {
            "current_driver": self.__user,
            "lap_time": p_time,
            "lap_valid": p_valid,
            "type": self.calc_type(p_time, "lap", p_valid),
        }
        msg = self.__payload
        self.send_data(msg, self.__pynng_config["pynng"]["publishers"]["__pub_time"]["topics"]["lap_finished"])

    def send_lap_start(self) -> None:
        msg = self.__best_times
        self.send_data(msg, self.__pynng_config["pynng"]["publishers"]["__pub_time"]["topics"]["lap_start"])

    def send_data(self, p_dict: dict, p_topic: str) -> None:
        json_data = json.dumps(p_dict)
        p_topic += " "
        msg = p_topic + json_data
        print(msg)
        self.__pub_time.send(msg.encode())

    def draw(self) -> None:
        """
        reads the new frame, loops through the checkpoints and draws them on the picture. Then the frame is published
        via pynng and showed

        Input/Output:
            None
        """
        self.__read_new_frame()
        for checkpoint in self.__checkpoints:
            checkpoint.draw_checkpoint(self.__frame)

        self.publish_frame()
        cv2.imshow("Debug", self.__frame)

        if cv2.waitKey(1) & 0xFF == ord("s"):
            cv2.destroyAllWindows()

    def __define_frame_receiver(self) -> None:
        """
        defines pynng receiver for the frame
        Returns:
            None
        """
        self.__sub_frame = pynng.Sub0()
        self.__sub_frame.subscribe("")
        self.__sub_frame.dial(self.__pynng_config["pynng"]["subscribers"]["__sub_frame"]["address"])

    def __read_new_frame(self) -> None:
        """
        Reads the next frame in the video.

        Input/Output:
        None
        """
        image = self.__sub_frame.recv()
        if self.__test is False:
            self.__frame = np.frombuffer(image, dtype=np.uint8).reshape((480, 640, 3))
        else:
            self.__frame = np.frombuffer(image, dtype=np.uint8).reshape((990, 1332, 3))

    def publish_frame(self) -> None:
        """
        sends the edited frame via pynng

        Input/Output:
        None
        """
        frame_np_array = np.array(self.__frame)
        frame_bytes = frame_np_array.tobytes()
        self.__pub_frame.send(frame_bytes)

    def __define_user_receiver(self) -> None:
        """
        defines pynng receiver for the current driver
        Returns:
            None
        """
        self.__sub_user = pynng.Sub0()
        self.__sub_user.subscribe(self.__pynng_config["pynng"]["subscribers"]["__sub_user"]["topics"]["current_driver"])
        self.__sub_user.dial(self.__pynng_config["pynng"]["subscribers"]["__sub_user"]["address"])

    def receive_user(self) -> str | None:
        """
        tries to receive a new user, if no new user was sent it passes

        Returns: str, None
        """
        try:
            msg = self.__sub_user.recv(block=False)
            msg = msg.decode("utf-8")
            i = msg.find(" ")
            data = msg[i + 1 :]
            return data
        except pynng.TryAgain:
            return None

    def change_user(self, p_name) -> None:
        self.__user = p_name
        self.__pers_best_times = {
            "sector_1_best_time": 1000.0,
            "sector_2_best_time": 1000.0,
            "sector_3_best_time": 1000.0,
            "lap_best_time": 1000.0,
        }


class Point:
    def __init__(self, p_coordinates: tuple) -> None:
        self.__x = p_coordinates[0]
        self.__y = p_coordinates[1]

    def __getitem__(self, key=0) -> int:
        item = (self.__x, self.__y)
        return item[key]

    def get_x(self) -> int:
        return self.__x

    def get_y(self) -> int:
        return self.__y

    def prf_area(self, p2, sx, sy) -> bool:
        """
        checks if the intersection is on the calculated lines
        Args:
            p2: checkpoint coordinate
            sx: intersection x coordinate
            sy: intersection y coordinate
        Returns: boolean

        """
        if min(self[0], p2[0]) <= sx <= max(self[0], p2[0]) and min(self[1], p2[1]) <= sy <= max(self[1], p2[1]):
            return True
        return False

    def calc_intersection(self, p_point, p_checkpoint) -> bool:
        """
        calculates the intersection of 2 infinite lines using vectors and then checking if the intersection is on the
        checkpoint pixels
        Args:
            p_point: list of 2 points received from the vehicle tracking module
            p_checkpoint: the checkpoint with that the intersection shouldbe checked
        Returns: boolean
        """

        def det(a, b):
            return a[0] * b[1] - a[1] * b[0]

        p1 = Point((p_checkpoint.get_x1(), p_checkpoint.get_y1()))
        p2 = Point((p_checkpoint.get_x2(), p_checkpoint.get_y2()))
        q1 = Point((self.get_x(), self.get_y()))
        q2 = Point((p_point.get_x(), p_point.get_y()))

        xdiff = (p1[0] - p2[0], q1[0] - q2[0])
        ydiff = (p1[1] - p2[1], q1[1] - q2[1])

        div = det(xdiff, ydiff)
        if div == 0:
            return False

        d = (det(*(p1, p2)), det(*(q1, q2)))
        x = det(d, xdiff) / div
        y = det(d, ydiff) / div

        if p1.prf_area(p2, x, y) & q1.prf_area(q2, x, y):
            return True
        return False


class Checkpoint:
    def __init__(self, checkpoint: dict, p_num: int) -> None:
        self.__x1 = checkpoint["x1"]
        self.__y1 = checkpoint["y1"]
        self.__x2 = checkpoint["x2"]
        self.__y2 = checkpoint["y2"]
        self.__crossed = False
        self.__num = p_num

    def draw_checkpoint(self, img) -> None:
        """
        Draws the checkpoints on the picture

        Input/Output:
        `None`
        """
        pts = np.array([[self.__x1, self.__y1], [self.__x2, self.__y2]])
        pts = pts.reshape((-1, 1, 2))
        cv2.polylines(img, [pts], True, (0, 0, 255), 3)

    def check_line(
        self,
        p_points: list,
    ) -> bool:
        """
        checks if the car drives through the given Pixels
        input:
            p_points: list of coordinates received from the vehicle tracking
        Returns: boolean
        """
        if p_points[0].calc_intersection(p_points[1], self):
            self.__crossed = True
            return True
        return False

    def get_crossed(self) -> bool:
        return self.__crossed

    def set_crossed(self, x: bool) -> None:
        self.__crossed = x

    def get_num(self) -> int:
        return self.__num

    def get_x1(self) -> int:
        return self.__x1

    def get_x2(self) -> int:
        return self.__x2

    def get_y1(self) -> int:
        return self.__y1

    def get_y2(self) -> int:
        return self.__y2


class FinishLineCheckpoint(Checkpoint):
    def __init__(self, checkpoint: dict, p_num: int) -> None:
        super().__init__(checkpoint, p_num)

    def check(self, coordinates: list) -> bool:
        if self.get_crossed() is False:
            if self.check_line(coordinates):
                run_scheduled_task(2, self.set_crossed, False)
                return True
        return False


class SectorLineCheckpoint(Checkpoint):
    def __init__(self, checkpoint: dict, p_num: int) -> None:
        super().__init__(checkpoint, p_num)

    def check(self, coordinates: list) -> bool:
        if self.get_crossed() is False:
            if self.check_line(coordinates):
                return True
        return False


class CheckpointDefiner:
    # Initialization
    def __init__(self, p_use_camera_stream: bool = True, video_path: str = "") -> None:
        """
        Initializes the class.

        Input:

            Debugging Only (!!DO NOT USE!!):
            `use_camera_stream:bool = True` -> If set to false it will show the video on the given `video_path`
            `video_path:str = ""` -> If use_camera_stream is set to false it will try to read this video

        Output:
        `None`
        """
        self.__close = False
        self.__roi_points: list = []
        self.__click = 0
        self.__checkpoints: dict = {"checkpoints": []}
        self.__use_camera_stream: bool = p_use_camera_stream

        self.__pynng_config = read_config("time_tracking_config.json")

        self.__define_cap(video_path)
        self.__define_windows()

    def __define_cap(self, video_path: str) -> None:
        """
        Defines the video cap.

        Input: `video_path:str` -> if `use_camera_stream=True` then enter the video path else leave it as a blank
        string (Debugging)

        Output:
        `None`
        """
        if self.__use_camera_stream:
            self.__define_image_receiver()
            self.__RESHAPE_VIDEO_SIZE = (480, 640, 3)
            # self.__RESHAPE_VIDEO_SIZE = (990, 1332, 3)
            self.__read_new_frame()
        else:
            self.__video_cap = cv2.VideoCapture(video_path)
            success, self.__frame = self.__video_cap.read()
            if not success:
                raise FileNotFoundError("Could not read the first frame of the video.")

    def __define_image_receiver(self) -> None:
        """
        Defines the image receiver, so it can receive the images from the  time_tracking module.

        Input/Output:
        `None`
        """
        self.__frame_receiver = pynng.Sub0()
        self.__frame_receiver.subscribe("")
        self.__frame_receiver.dial(self.__pynng_config["pynng"]["subscribers"]["__sub_coordinates"]["address"])

    def __define_windows(self) -> None:
        """
        Defines the Windows to be used by `cv2.imshow()`

        Input/Output:
        `None`
        """
        cv2.namedWindow("Point Drawer")

        cv2.setMouseCallback("Point Drawer", self.__mouse_event_handler)

    # Mouse Handler
    def __mouse_event_handler(self, event: int, x: int, y: int, _flags, _params) -> None:
        """
        A function that handles the mouse events from `cv2.setMouseCallback()`

        Input:
        `event:int` -> The event that has been fired
        `x:int` -> The x position of the cursor
        `y:int` -> The y position of the cursor
        `_flags` -> Placeholder
        `_params` -> Placeholder

        Output:
        `None`
        """

        if event == cv2.EVENT_LBUTTONDOWN:
            self.__click += 1
            if self.__click != 2:
                self.__helper = (x, y)
            else:
                self.__roi_points.append([self.__helper, (x, y)])
                self.__click = 0

        elif event == cv2.EVENT_RBUTTONDOWN:
            self.__roi_points.pop()
        elif event == cv2.EVENT_MBUTTONDOWN:
            self.__click = 0
            self.__roi_points = []

    # Helper Functions
    def __read_new_frame(self) -> None:
        """
        Reads the next frame in the video.

        Input/Output:
        `None`
        """
        if self.__use_camera_stream:
            frame_bytes = self.__frame_receiver.recv()
            frame = np.frombuffer(frame_bytes, dtype=np.uint8)
            self.__frame = frame.reshape(self.__RESHAPE_VIDEO_SIZE)
        else:
            success, self.__frame = self.__video_cap.read()
            if not success:
                raise IndexError("Frame could not be read. Video probably ended.")

    def __draw_on_frame(self) -> None:
        """
        Draws the checkpoints on the picture

        Input/Output:
        `None`
        """
        self.__lined_frame = self.__frame.copy()
        if len(self.__roi_points) >= 1:
            for line in self.__roi_points:
                self.__lined_frame = cv2.polylines(self.__lined_frame, [np.array(line)], True, (0, 0, 255), 2)
            self.__updated_frame = np.zeros_like(self.__frame)

    def __show_images(self) -> None:
        """
        Shows the image to the `cv2.namedWindow()` using `cv2.imshow()`.

        Input/Output:
        `None`
        """
        cv2.imshow("Point Drawer", self.__lined_frame)

    def __check_to_close(self) -> None:
        """
        Uses `cv2.waitKey()` to check if the user wants to quit the program

        Input/Output:
        None
        """

        if cv2.waitKey(1) & 0xFF == ord("q"):
            cv2.destroyAllWindows()
            self.__save_config()
            self.__close = True

    def __save_config(self) -> None:
        """
        Saves the coordinates to the `time_tracking.json` file.

        Input/Output:
        None
        """
        for line in self.__roi_points:
            self.__checkpoints["checkpoints"].append(
                {"x1": line[0][0], "y1": line[0][1], "x2": line[1][0], "y2": line[1][1]}
            )
        with open("time_tracking.json", "w") as f:
            json.dump(self.__checkpoints, f, indent=4)

    # Main Functions
    def main(self) -> None:
        """
        Is a loop that goes through the Camera Stream. !DEBUGGING ONLY: Uses video instead of camera stream.!

        Input/Output:
        None
        """
        while self.__close is False:
            self.__read_new_frame()
            self.__draw_on_frame()
            self.__show_images()
            self.__check_to_close()
