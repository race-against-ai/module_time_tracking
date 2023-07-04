# Copyright (C) 2022 NG:ITL
from time_tracking.time_tracking import Timer

if __name__ == '__main__':
    print("Time-tracking started")
    timer = Timer()
    timer.start_timer()
    while True:
        timer.run()
