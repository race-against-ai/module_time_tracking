# Copyright (C) 2023, NG:ITL
import json
import os
from pathlib import Path
from threading import Timer


def read_json(config_file_name: str) -> dict:
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
