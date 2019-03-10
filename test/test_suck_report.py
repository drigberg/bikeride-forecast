import json
import pytest
from datetime import datetime
from get_and_send_forecasts import SuckReport, Temp, Weather, Wind


def is_approximately(score, target, delta=2):
    return abs(score - target) <= delta


@pytest.fixture
def weather_data():
    with open('test/data/weather.json', 'rb') as f:
        data = json.loads(f.read())
    return data


class TestSuckReportUnit:
    def test_get_clouds_score(cls):
        assert SuckReport.get_clouds_score(0) == 0
        assert SuckReport.get_clouds_score(100) == 5
        assert SuckReport.get_clouds_score(20) == 1
        assert SuckReport.get_clouds_score(25) == 1.25

    def test_get_wind_score(cls):
        assert SuckReport.get_wind_score(Wind(speed=0, deg=90), 90) == 0
        assert SuckReport.get_wind_score(Wind(speed=5, deg=90), 90) == -0.1
        assert SuckReport.get_wind_score(Wind(speed=7.5, deg=90), 90) == -0.15
        assert SuckReport.get_wind_score(Wind(speed=15, deg=90), 90) == -0.3
        assert SuckReport.get_wind_score(Wind(speed=15, deg=180), 90) == 1.27
        assert SuckReport.get_wind_score(Wind(speed=5, deg=270), 90) == 0.95
        assert SuckReport.get_wind_score(Wind(speed=15, deg=180), 0) == 2.85

    def test_get_rain_score(cls):
        assert SuckReport.get_rain_score(0) == 0
        assert SuckReport.get_rain_score(0.2) == 5.2
        assert SuckReport.get_rain_score(1) == 6
        assert SuckReport.get_rain_score(1.4) == 6.4

    def test_get_temp_score_in_ideal_range(cls):
        assert SuckReport.get_temp_score(Temp(min=13, max=13), 0) == 0
        assert SuckReport.get_temp_score(Temp(min=20.5, max=21), 0) == 0
        assert SuckReport.get_temp_score(Temp(min=20, max=21.5), 0) == 0
        assert SuckReport.get_temp_score(Temp(min=13.3, max=23.5), 0) == 0
        assert SuckReport.get_temp_score(Temp(min=17, max=24), 0) == 0
        assert SuckReport.get_temp_score(Temp(min=19, max=22), 0) == 0
        assert SuckReport.get_temp_score(Temp(min=24, max=24), 0) == 0

    def test_get_temp_score_below_ideal_range(cls):
        assert SuckReport.get_temp_score(Temp(min=7, max=7), 0) == 2.4
        assert SuckReport.get_temp_score(Temp(min=2, max=7), 0) == 3.4
        assert SuckReport.get_temp_score(Temp(min=-3, max=2), 0) == 5.4
        assert SuckReport.get_temp_score(Temp(min=7, max=7), 100) == 2.4
        assert SuckReport.get_temp_score(Temp(min=2, max=7), 100) == 3.4
        assert SuckReport.get_temp_score(Temp(min=-3, max=2), 100) == 5.4

    def test_get_temp_score_above_ideal_range(cls):
        assert SuckReport.get_temp_score(Temp(min=27.5, max=27.5), 0) == 1
        assert SuckReport.get_temp_score(Temp(min=30, max=30), 0) == 2
        assert SuckReport.get_temp_score(Temp(min=35, max=35), 0) == 4
        assert SuckReport.get_temp_score(Temp(min=35, max=45), 0) == 6
        assert SuckReport.get_temp_score(Temp(min=30, max=30), 100) == 4
        assert SuckReport.get_temp_score(Temp(min=35, max=35), 100) == 8
        assert SuckReport.get_temp_score(Temp(min=35, max=45), 100) == 12

    def test_get_temp_score_mixed(cls):
        assert SuckReport.get_temp_score(Temp(min=20, max=35), 0) == 2
        assert SuckReport.get_temp_score(Temp(min=7, max=20), 0) == 1.2
        assert SuckReport.get_temp_score(Temp(min=7, max=35), 0) == 3.2


class TestSuckReportIntegration:
    def test_suck_report_wind_direction(cls):
        weather = Weather(
            clouds=50,
            dt=0,
            humidity=60,
            rain=1.4,
            temp=Temp(min=20, max=30),
            wind=Wind(speed=40, deg=90))

        def calc(travel_direction):
            return SuckReport.create(weather, travel_direction).total

        assert is_approximately(calc(90), 10)
        assert calc(60) > calc(90)
        assert calc(180) > calc(60)
        assert calc(0) == calc(180)
        assert calc(240) > calc(180)
        assert calc(270) > calc(240)

    def test_suck_report_freezing_windy(cls):
        weather = Weather(
            clouds=100,
            dt=0,
            humidity=0,
            rain=0,
            temp=Temp(min=-10, max=-5),
            wind=Wind(speed=20, deg=270))
        score = SuckReport.create(weather, 90).total
        assert is_approximately(score, 18)

    def test_suck_report_freezing_dry_cloudy(cls):
        weather = Weather(
            clouds=100,
            dt=0,
            humidity=0,
            rain=0,
            temp=Temp(min=-10, max=-5),
            wind=Wind(speed=0, deg=90))
        score = SuckReport.create(weather, 90).total
        assert is_approximately(score, 12)

    def test_suck_report_hot_humid_rainy(cls):
        weather = Weather(
            clouds=100,
            dt=0,
            humidity=100,
            rain=2,
            temp=Temp(min=30, max=35),
            wind=Wind(speed=0, deg=90))
        score = SuckReport.create(weather, 90).total
        assert is_approximately(score, 20)

    def test_suck_report_ideal_rainy_windy(cls):
        weather = Weather(
            clouds=100,
            dt=0,
            humidity=0,
            rain=1.5,
            temp=Temp(min=18, max=22),
            wind=Wind(speed=20, deg=270))
        score = SuckReport.create(weather, 90).total
        assert is_approximately(score, 15)

    def test_suck_report_ideal_rainy(cls):
        weather = Weather(
            clouds=100,
            dt=0,
            humidity=0,
            rain=1.5,
            temp=Temp(min=18, max=22),
            wind=Wind(speed=0, deg=90))
        score = SuckReport.create(weather, 90).total
        assert is_approximately(score, 12)

    def test_suck_report_perfect(cls):
        weather = Weather(
            clouds=0,
            dt=0,
            humidity=0,
            rain=0,
            temp=Temp(min=18, max=22),
            wind=Wind(speed=0, deg=90))
        score = SuckReport.create(weather, 90).total
        assert is_approximately(score, 0, delta=0.5)

    def test_suck_report_incredible(cls):
        weather = Weather(
            clouds=0,
            dt=0,
            humidity=0,
            rain=0,
            temp=Temp(min=18, max=22),
            wind=Wind(speed=10, deg=90))
        score = SuckReport.create(weather, 90).total
        assert is_approximately(score, -1, delta=1)

    def test_create_for_trip(cls, weather_data):
        # cold, but a tailwind
        assert is_approximately(
            score=SuckReport.create_for_trip(
                weather_data=weather_data,
                day=datetime.fromtimestamp(1550264400),
                time=1000,
                pointA=(90, 90),
                pointB=(91, 90)).total,
            target=5)

        # rainy
        assert is_approximately(
            score=SuckReport.create_for_trip(
                weather_data=weather_data,
                day=datetime.fromtimestamp(1550588400),
                time=1000,
                pointA=(90, 90),
                pointB=(91, 90)).total,
            target=7)
