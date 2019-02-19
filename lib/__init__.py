import dataclasses
import datetime
import json
import logging
import math
import typing
from tornado import httpclient
from mapbox import Directions

logger = logging.getLogger(__name__)


def get_secrets():
    with open('secrets.json', 'rb') as f:
        secrets = json.loads(f.read())
    return secrets

def get_directions(pointA: tuple, pointB: tuple):
    secrets = get_secrets()
    service = Directions(access_token=secrets['mapbox_api_key'])
    origin = {
        'type': 'Feature',
        'properties': {'name': 'Portland, OR'},
        'geometry': {
            'type': 'Point',
            'coordinates': list(pointA)
        }
    }
    destination = {
        'type': 'Feature',
        'properties': {'name': 'Bend, OR'},
        'geometry': {
            'type': 'Point',
            'coordinates': list(pointB)
        }
    }
    response = service.directions([origin, destination])
    assert response.status_code == 200
    return response.geojson()


def calc_difference_between_vectors(deg1: float, deg2: float):
    diff = abs(deg1 - deg2)
    if diff > 180:
        diff = 360 - diff
    return diff

def calc_degrees_north_from_coords(pointA: tuple, pointB: tuple) -> float:
    height = pointB[1] - pointA[1]
    width = pointB[0] - pointA[0]
    hypotenuse = math.sqrt(math.pow(height, 2) + math.pow(width, 2))
    deg = math.degrees(math.asin(height/hypotenuse))

    # Q1, Q2
    if width >= 0:
        deg = 90 - deg
    # Q3
    else:
        deg = 270 + deg
    return round(deg, 2)

def get_weather_data(coords: tuple) -> typing.Mapping:
    secrets = get_secrets()
    weather_api_key = secrets['weather_api_key']
    base_url = "http://api.openweathermap.org/data/2.5/forecast"
    api_client = tornado.httpclient.HTTPClient()
    request = httpclient.HTTPRequest(
        url=f"{base_url}?lat={coords[0]}&lon={coords[1]}&APPID={weather_api_key}&units=metric",
        headers={
            "Accept": "application/json"
        },
        connect_timeout=60,
        request_timeout=60
    )
    response = api_client.fetch(request)
    return response.body

@dataclasses.dataclass
class Wind:
    speed: float
    deg: float

@dataclasses.dataclass
class Temp:
    min: float
    max: float

@dataclasses.dataclass
class Weather:
    clouds: int
    dt: int
    humidity: float
    rain: float
    temp: Temp
    wind: Wind

    @classmethod
    def get_weather_at_time(cls, weather_data: dict, time: datetime.datetime):
        dt = time.timestamp()
        closest_item = None
        for item in weather_data["list"]:
            time_delta = abs(item["dt"] - dt)
            if closest_item is None or time_delta < closest_item["time_delta"]:
                closest_item = {
                    "item": item,
                    "time_delta": time_delta
                }
        return cls.create_from_weather_data(closest_item['item'])

    @classmethod
    def create_from_weather_data(cls, data: dict):
        if data['wind']:
            wind = Wind(
                speed=data['wind']['speed'],
                deg=data['wind']['deg'])
        else:
            wind = Wind(
                speed=0,
                deg=0)
        return cls(
            clouds=data['clouds']['all'] if data['clouds'] else 0,
            dt=data['dt'],
            humidity=data['main']['humidity'],
            rain=data['rain']['3h'] if data['rain'] else 0,
            temp=Temp(
                min=data['main']['temp_min'],
                max=data['main']['temp_max']
            ),
            wind=wind
        )

class SuckIndex:
    IDEAL_TEMPERATURE_RANGE = range(13, 25)

    @classmethod
    def get_index(cls, weather: Weather, travel_direction: float):
        scores = [
            cls.get_temp_score(weather.temp, weather.humidity),
            cls.get_wind_score(weather.wind, travel_direction),
            cls.get_rain_score(weather.rain),
            cls.get_clouds_score(weather.clouds),
        ]
        return sum(scores)

    @classmethod
    def get_index_for_trip(
            cls,
            weather_data: Weather,
            day: datetime.datetime,
            time: int,
            pointA: tuple,
            pointB: tuple):
        direction = calc_degrees_north_from_coords(pointA, pointB)

        hour = int(time / 100)
        minute = int(time - hour * 100)

        weather = Weather.get_weather_at_time(weather_data, datetime.datetime(
            year=day.year,
            month=day.month,
            day=day.day,
            hour=hour,
            minute=minute,
            second=0))
        return cls.get_index(weather, direction)
    @classmethod
    def get_rain_score(cls, rain: float):
        return rain * 5

    @classmethod
    def get_wind_direction_multiplier(cls, travel_deg: float, wind_deg: float):
        """
        Tailwind is pretty good: -1x.
        Serious crosswind sucks: 2x.
        Any headwind sucks: 5x.
        """
        diff = calc_difference_between_vectors(travel_deg, wind_deg)
        return diff / 30 - 1

    @classmethod
    def get_clouds_score(cls, clouds: int):
        """ maximum 5 points """
        return clouds / 100 * 5

    @classmethod
    def get_humidity_multiplier(cls, humidity: int):
        return 1 + (humidity / 100)

    @classmethod
    def get_temp_score(cls, temp: Temp, humidity: float):
        """
        Suckiness is based on distance from ideal range.
        Final value is average of min and max scores.
        """
        indexes = []
        for t in [temp.min, temp.max]:
            index = 0
            if t < cls.IDEAL_TEMPERATURE_RANGE.start:
                index = cls.IDEAL_TEMPERATURE_RANGE.start - t
            elif t > cls.IDEAL_TEMPERATURE_RANGE.stop:
                humidity_multiplier = cls.get_humidity_multiplier(humidity)
                index = (t - cls.IDEAL_TEMPERATURE_RANGE.stop) * humidity_multiplier
            indexes.append(index)
        average = (indexes[0] + indexes[1]) / 2

        return average / 2.5

    @classmethod
    def get_wind_score(cls, wind: Wind, travel_direction: float):
        """
        Tailwind is great and all, but if it's too windy, it's still
        gonna suck, so we only apply the multiplier to some of the score.
        """
        base_score = wind.speed / 20
        multiplier = cls.get_wind_direction_multiplier(
            travel_direction,
            wind.deg)
        modifiable_score = base_score * 0.7
        static_score = base_score * 0.3
        score = modifiable_score * multiplier + static_score
        return round(score, 2)


