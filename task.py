from .lib import get_index_for_trip, get_weather_data, SuckIndex
from datetime import datetime


def task():
    with open('store.json', 'rb') as f:
        subscriptions = f.read()
    for subscription in subscriptions:
        home = tuple(subscription['home'])
        dest = tuple(subscription['dest'])
        midway_point = (
            (home[0] + dest[0]) / 2,
            (home[1] + dest[1]) / 2
        )

        departure_time = subscription['departure']
        return_time = subscription['return']
        name = subscription['name']
        email = subscription['email']

        weather_data = get_weather_data(midway_point)
        departure_index = get_index_for_trip(
            weather_data=weather_data,
            day=datetime.today(),
            time=departure_time,
            pointA=home,
            pointB=dest)
        return_index = SuckIndex.get_index_for_trip(
            weather_data=weather_data,
            day=datetime.today(),
            time=return_time,
            pointA=dest,
            pointB=home)

        print(f"Hey {name}<{email}>!")
        print(f"\tSuckIndex for departure at {departure_time}: {index}")
        print(f"\tSuckIndex for return at {return_time}: {index}")

if __name__ == "__main__":
    task()