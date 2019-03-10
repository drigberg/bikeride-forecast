import json
import pytest
from datetime import datetime
from get_and_send_forecasts import Weather


@pytest.fixture
def weather_data():
    with open('test/data/weather.json', 'rb') as f:
        data = json.loads(f.read())
    return data


class TestWeather:
    def test_get_weather_at_time_exact(cls, weather_data):
        time = datetime.fromtimestamp(1550296800)
        weather = Weather.get_weather_at_time(weather_data, time)
        assert weather.dt == 1550296800

    def test_get_weather_at_time_early(cls, weather_data):
        time = datetime.fromtimestamp(1550329000)
        weather = Weather.get_weather_at_time(weather_data, time)
        assert weather.dt == 1550329200

    def test_get_weather_at_time_late(cls, weather_data):
        time = datetime.fromtimestamp(1550330000)
        weather = Weather.get_weather_at_time(weather_data, time)
        assert weather.dt == 1550329200
