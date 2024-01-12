# Copyright (C) 2023, NG:ITL
import json
import cv2
import pynng
import numpy as np

from time_tracking.utils import read_config


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

        with open("./time_tracking_config.json", "r") as file:
            self.__pynng_config = json.load(file)

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
            # self.__RESHAPE_VIDEO_SIZE = (480, 640, 3)
            self.__RESHAPE_VIDEO_SIZE = (990, 1332, 3)
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
        self.__frame_receiver.dial(self.__pynng_config["pynng"]["subscribers"]["__sub_frame"]["address"])

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


if __name__ == "__main__":
    checkpoint_definer = CheckpointDefiner()
    checkpoint_definer.main()
