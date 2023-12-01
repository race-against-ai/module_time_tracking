# Copyright (C) 2022 NG:ITL
from time_tracking.time_tracking import LapTimer


def main(testing: bool = False):
    print("Time-tracking started")
    timer = LapTimer(test=testing)
    timer.start_timer()
    while True:
        timer.run()


if __name__ == "__main__":
    main()
