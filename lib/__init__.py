import dataclasses
import datetime
import json
import logging
import math
import pathlib
import typing
from mapbox import Directions
from tornado import httpclient

logger = logging.getLogger(__name__)

IDEAL_TEMPERATURE_RANGE = range(13, 25)

@dataclasses.dataclass(frozen=True)
class Subscription:
    name: str
    email: str
    home: typing.Sequence[float]
    dest: typing.Sequence[float]
    departure_time: int
    return_time: int

    @classmethod
    def from_data(cls, data):
        assert isinstance(data['name'], str)
        assert isinstance(data['email'], str)
        assert isinstance(data['departure_time'], int)
        assert isinstance(data['return_time'], int)
        assert len(data['home']) == 2, 'Invalid home coords'
        assert len(data['dest']) == 2, 'Invalid dest coords'

        return cls(
            name=data['name'],
            email=data['email'],
            home=data['home'],
            dest=data['dest'],
            departure_time=data['departure_time'],
            return_time=data['return_time'])

    def to_serializable(self):
        return {
            "name": self.name,
            "email": self.email,
            "home": self.home,
            "dest": self.dest,
            "departure_time": self.departure_time,
            "return_time": self.return_time,
        }

def get_secrets():
    secrets_file = pathlib.Path('lib/secrets.json')
    return json.loads(secrets_file.read_text())

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
    """ delta_lat --> height, delta_lon --> width """
    width = pointB[1] - pointA[1]
    height = pointB[0] - pointA[0]
    hypotenuse = math.sqrt(math.pow(height, 2) + math.pow(width, 2))
    deg = math.degrees(math.asin(height/hypotenuse))

    # Q1, Q2
    if width >= 0:
        deg = 270 - deg
    # Q3
    else:
        deg = 90 + deg
    if deg == 360:
        deg = 0
    return round(deg, 2)

async def get_weather_data(coords: tuple) -> typing.Mapping:
    logger.debug('Getting weather data for %s', coords)
    secrets = get_secrets()
    weather_api_key = secrets['weather_api_key']
    base_url = "http://api.openweathermap.org/data/2.5/forecast"
    api_client = httpclient.AsyncHTTPClient()
    request = httpclient.HTTPRequest(
        url=f"{base_url}?lat={coords[0]}&lon={coords[1]}&APPID={weather_api_key}&units=metric",
        headers={
            "Accept": "application/json"
        },
        connect_timeout=60,
        request_timeout=60
    )
    try:
        response = await api_client.fetch(request)
        weather_data = json.loads(response.body.decode('utf-8'))
    except Exception as esc:
        logger.error(esc.response.body)
        raise esc
    logger.debug('Got weather data: %s', weather_data)
    import pdb; pdb.set_trace()
    return weather_data

@dataclasses.dataclass(frozen=True)
class Wind:
    speed: float  # km/hour
    deg: float  # meteorological degrees north (0 == wind from north to south)

@dataclasses.dataclass(frozen=True)
class Temp:
    min: float  # Celcius
    max: float  # Celcius

@dataclasses.dataclass(frozen=True)
class Weather:
    clouds: int  # %
    dt: int  # timestamp
    humidity: float  # %
    rain: float  # mm / 3h
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
        if 'wind' in data:
            wind = Wind(
                speed=data['wind']['speed'],
                deg=data['wind']['deg'])
        else:
            wind = Wind(
                speed=0,
                deg=0)

        if 'rain' in data and '3h' in data['rain']:
            rain = data['rain']['3h']
        else:
            rain = 0

        if 'clouds' in data and 'all' in data['clouds']:
            clouds = data['clouds']['all']
        else:
            clouds = 0

        return cls(
            clouds=clouds,
            dt=data['dt'],
            humidity=data['main']['humidity'],
            rain=rain,
            temp=Temp(
                min=data['main']['temp_min'],
                max=data['main']['temp_max']
            ),
            wind=wind
        )


@dataclasses.dataclass(frozen=True)
class SuckReport:
    temp: float
    wind: float
    rain: float
    clouds: float
    weather: Weather
    travel_direction: float

    @property
    def total(self) -> float:
      return self.temp + self.wind + self.rain + self.clouds

    @classmethod
    def create(cls, weather: Weather, travel_direction: float):
        return cls(
            temp=cls.get_temp_score(weather.temp, weather.humidity),
            wind=cls.get_wind_score(weather.wind, travel_direction),
            rain=cls.get_rain_score(weather.rain),
            clouds=cls.get_clouds_score(weather.clouds),
            weather=weather,
            travel_direction=travel_direction)

    @classmethod
    def create_for_trip(
            cls,
            weather_data: Weather,
            day: datetime.datetime,
            time: int,
            pointA: tuple,
            pointB: tuple):
        direction = calc_degrees_north_from_coords(pointA, pointB)
        hour = int(time / 100)
        minute = int(time - hour * 100)
        date = datetime.datetime(
            year=day.year,
            month=day.month,
            day=day.day,
            hour=hour,
            minute=minute,
            second=0)
        weather = Weather.get_weather_at_time(weather_data, date)
        return cls.create(weather, direction)

    @classmethod
    def get_rain_score(cls, rain: float):
        """any rain sucks."""
        if rain == 0:
            score = 0
        else:
            score = 5 + rain
        return round(score, 2)
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
        score = clouds / 100 * 5
        return round(score, 2)

    @classmethod
    def get_humidity_multiplier(cls, humidity: int):
        return 1 + (humidity / 100)

    @classmethod
    def get_temp_score(cls, temp: Temp, humidity: float):
        """
        Suckiness is based on distance from ideal range.
        Final value is average of min and max scores.
        """
        scores = []
        for t in [temp.min, temp.max]:
            score = 0
            if t < IDEAL_TEMPERATURE_RANGE.start:
                score = IDEAL_TEMPERATURE_RANGE.start - t
            elif t > IDEAL_TEMPERATURE_RANGE.stop:
                humidity_multiplier = cls.get_humidity_multiplier(humidity)
                score = (t - IDEAL_TEMPERATURE_RANGE.stop) * humidity_multiplier
            scores.append(score)
        average = (scores[0] + scores[1]) / 2
        total = average / 2.5
        return round(total, 2)

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

def create_email_contents(sub: Subscription, departure_report: SuckReport, return_report: SuckReport) -> (str, str):
    text = f"Hey {sub.name}!" \
           f"\tTotal suckiness for departure at {sub.departure_time}: {departure_report.total}" \
           f"\t\tWind: {departure_report.wind}" \
           f"\t\tTemp: {departure_report.temp}" \
           f"\t\tRain: {departure_report.rain}" \
           f"\t\tClouds: {departure_report.clouds}" \
           f"\tTotal suckiness for return at {sub.return_time}: {return_report.total}" \
           f"\t\tWind: {return_report.wind}" \
           f"\t\tTemp: {return_report.temp}" \
           f"\t\tRain: {return_report.rain}" \
           f"\t\tClouds: {return_report.clouds}" \
           f"\nReminder: < 5 is great; 5-10 is fine; 11-15 sucks; 16-20 is horrendous; 21+ is a legendary failure."

    html = """\
    <html>
    <head></head>
    <body>
        <h1>Hey {sub.name}!</h2>
        <h3>Departure at {sub.departure_time}, traveling at {departure_report.travel_direction} degrees north</h3>
        <h4>Total suckiness: {departure_report.total} points</h4>
        <ul>
            <li>
                Wind: {departure_report.wind} points
                <ul>
                    <li>Speed: {departure_report.weather.wind.speed} km/hour</li>
                    <li>Direction: {departure_report.weather.wind.deg} degrees north</li>
                </ul>
            </li>
            <li>
                Temp: {departure_report.temp} points
                <ul>
                    <li>Min: {departure_report.weather.temp.min} degrees Celcius</li>
                    <li>Max: {departure_report.weather.temp.max} degrees Celcius</li>
                    <li>Humidity: {departure_report.weather.humidity}%</li>
                </ul>
            </li>
            <li>
                Rain: {departure_report.rain} points
                <ul>
                    <li>{departure_report.weather.rain} mm/3h</li>
                </ul>
            </li>
            <li>
                Clouds: {departure_report.clouds} points
                <ul>
                    <li>{departure_report.weather.clouds}%</li>
                </ul>
            </li>
        </ul>
        <h3>Return at {sub.return_time}, traveling at {return_report.travel_direction} degrees north</h3>
        <h4>Total suckiness: {return_report.total} points</h4>
        <ul>
            <li>
                Wind: {return_report.wind} points
                <ul>
                    <li>Speed: {return_report.weather.wind.speed} km/hour</li>
                    <li>Direction: {return_report.weather.wind.deg} degrees north</li>
                </ul>
            </li>
            <li>
                Temp: {return_report.temp} points
                <ul>
                    <li>Min: {return_report.weather.temp.min} degrees Celcius</li>
                    <li>Max: {return_report.weather.temp.max} degrees Celcius</li>
                    <li>Humidity: {return_report.weather.humidity}%</li>
                </ul>
            </li>
            <li>
                Rain: {return_report.rain} points
                <ul>
                    <li>{return_report.weather.rain} mm/3h</li>
                </ul>
            </li>
            <li>
                Clouds: {return_report.clouds} points
                <ul>
                    <li>{return_report.weather.clouds}%</li>
                </ul>
            </li>
        </ul>
        <br>
        <em>Reminder for point totals: < 5 is great; 5-10 is fine; 11-15 sucks; 16-20 is horrendous; 21+ is a legendary failure.</em>
    </body>
    </html>
    """.format(
        sub=sub,
        departure_report=departure_report,
        return_report=return_report
    )

    return (text, html)