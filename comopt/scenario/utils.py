from datetime import datetime, time, timedelta


def time_plus(start_time: time, duration: timedelta):
    start = datetime(
        2000, 1, 1,
        hour=start_time.hour, minute=start_time.minute, second=start_time.second)
    end = start + duration
    return end.time()


def time_duration(start_time: time, end_time: time) :
    start_datetime = datetime(
        2000, 1, 1,
        hour=start_time.hour, minute=start_time.minute, second=start_time.second)
    end_datetime = datetime(
        2000, 1, 1,
        hour=end_time.hour, minute=end_time.minute, second=end_time.second)
    duration = end_datetime - start_datetime
    return duration
