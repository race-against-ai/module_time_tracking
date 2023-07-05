# Copyright (C) 2022 NG:ITL
from time_tracking.time_tracking import LapTimer

if __name__ == '__main__':
    print("Time-tracking started")
    timer = LapTimer()
    timer.start_timer()
    while True:
        timer.run()
