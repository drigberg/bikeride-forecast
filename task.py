from . import lib


def task():
    weather_data = get_weather_data()
    # directions = get_directions((-122.7282, 45.5801), (-121.3153, 44.0582))
    weather = Weather.create_from_weather_data(weather_data)
    index = SuckIndex.get_index(weather)
    print(f'SuckIndex: {index}')

if __name__ == "__main__":
    task()