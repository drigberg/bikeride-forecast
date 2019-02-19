import json
import pathlib
import pytest
from datetime import datetime
from lib import Weather

@pytest.fixture
def weather_data():
    with open('test/data/weather.json', 'rb') as f:
        data = json.loads(f.read())
    return data

class TestWeather:
    def test_get_weather_at_time_exact(cls, weather_data):
        time = datetime(2019, 2, 16, 7, 0)
        weather = Weather.get_weather_at_time(time, weather_data)
        assert weather.dt == 1550296800

    def test_get_weather_at_time_early(cls, weather_data):
        time = datetime.fromtimestamp(1550329000)
        weather = Weather.get_weather_at_time(time, weather_data)
        assert weather.dt == 1550329200

    def test_get_weather_at_time_late(cls, weather_data):
        time = datetime.fromtimestamp(1550330000)
        weather = Weather.get_weather_at_time(time, weather_data)
        assert weather.dt == 1550329200
