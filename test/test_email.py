import json
import pytest
from datetime import datetime
from lib import create_email_contents, Subscription, SuckReport


@pytest.fixture
def weather_data():
    with open('test/data/weather.json', 'rb') as f:
        data = json.loads(f.read())
    return data

class TestEmail:
    def test_email_text(cls, weather_data):
        departure_report = SuckReport.create_for_trip(
                weather_data=weather_data,
                day=datetime.fromtimestamp(1550264400),
                time=900,
                pointA=(52.344, 4.9504),
                pointB=(2.3402, 4.8264))
        return_report = SuckReport.create_for_trip(
                weather_data=weather_data,
                day=datetime.fromtimestamp(1550264400),
                time=1800,
                pointA=(2.3402, 4.8264),
                pointB=(52.344, 4.9504))
        sub = Subscription(
            name='dan',
            email='dan@dan.dan',
            home=[52.344, 4.9504],
            dest=[2.3402, 4.8264],
            departure_time=900,
            return_time=1800
        )
        text, _ = create_email_contents(sub, departure_report, return_report)
        expected = 'Hey dan!\tTotal suckiness for departure at 900: 6.3\t\tWind: 1.13\t\tTemp: 4.57\t\tRain: 0\t\tClouds: 0.6\t' \
                 + 'Total suckiness for return at 1800: 11.5\t\tWind: 1.32\t\tTemp: 0.42\t\tRain: 5.16\t\tClouds: 4.6\n' \
                 + 'Reminder: < 5 is great; 5-10 is fine; 11-15 sucks; 16-20 is horrendous; 21+ is a legendary failure.'
        assert text == expected
