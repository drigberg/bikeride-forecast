import boto3
import dataclasses
import datetime
import json
import logging
import math
import smtplib
import typing
from botocore.vendored import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

IDEAL_TEMPERATURE_RANGE = range(13, 25)


def get_store():
    s3 = boto3.client("s3")
    res = s3.get_object(Bucket='bikeride-forecast', Key='store.json')
    store = json.loads(res["Body"].read())
    logger.info("Got store: %s", store)
    return store


def get_secrets():
    s3 = boto3.client("s3")
    res = s3.get_object(Bucket='bikeride-forecast', Key='secrets.json')
    secrets = json.loads(res["Body"].read())
    logger.info("Got secrets!")
    return secrets


def calc_difference_between_vectors(deg1: float, deg2: float):
    diff = abs(deg1 - deg2)
    if diff > 180:
        diff = 360 - diff
    return diff


def calc_degrees_north_from_coords(pointA: tuple, pointB: tuple) -> float:
    """
    delta_lat --> height, delta_lon --> width

    Example:
        home == 52.000, 5.100
        work == 52.000, 5.000

        deltaY == 0
        delta X == -0.1
        Direction == from east => 90 degrees north
    """

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


def get_weather_data(coords: tuple) -> typing.Mapping:
    logger.debug('Getting weather data for %s', coords)
    secrets = get_secrets()
    weather_api_key = secrets['weather_api_key']
    base_url = "http://api.openweathermap.org/data/2.5/forecast"

    url = f"{base_url}?lat={coords[0]}&lon={coords[1]}&APPID={weather_api_key}&units=metric"
    headers = {
        "Accept": "application/json"
    }

    weather_data = None
    try:
        res = requests.get(url, headers=headers)
        logger.info("Got response from weather api")
        weather_data = json.loads(res.text)
        logger.info("parsed response body!", weather_data)
    except Exception as esc:
        logger.error("ERROR", esc)
        raise esc
    logger.debug('Got weather data: %s', weather_data)
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
            clouds=0,  # clouds is currently removed
            # clouds=cls.get_clouds_score(weather.clouds),
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
        <h1>Hey {sub.name}!</h1>
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


def send_email(
        sub: Subscription,
        departure_report: SuckReport,
        return_report: SuckReport):
    logger.info('Sending email to %s!', sub.email)
    secrets = get_secrets()
    text, html = create_email_contents(sub, departure_report, return_report)

    from_address = secrets['email_user']
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "BikeRideForecast: Your Daily Report"
    msg['From'] = from_address
    msg['To'] = sub.email
    msg.attach(MIMEText(text, 'plain'))
    msg.attach(MIMEText(html, 'html'))

    smtp = smtplib.SMTP('smtp.gmail.com', 587)
    smtp.set_debuglevel(0)
    smtp.ehlo()
    smtp.starttls()
    smtp.ehlo()
    smtp.login(from_address, secrets["email_pass"])
    smtp.sendmail(from_address, sub.email, msg.as_string())
    smtp.quit()
    logger.info('Sent email to %s!', sub.email)


def send_notifications():
    logger.info('Sending notifications!')
    store = get_store()
    for subscription_data in store:
        sub = Subscription.from_data(subscription_data)
        home = tuple(sub.home)
        dest = tuple(sub.dest)
        midway_point = (
            round((home[0] + dest[0]) / 2, 6),
            round((home[1] + dest[1]) / 2, 6)
        )
        weather_data = get_weather_data(midway_point)
        departure_report = SuckReport.create_for_trip(
            weather_data=weather_data,
            day=datetime.datetime.today(),
            time=sub.departure_time,
            pointA=home,
            pointB=dest)
        return_report = SuckReport.create_for_trip(
            weather_data=weather_data,
            day=datetime.datetime.today(),
            time=sub.return_time,
            pointA=dest,
            pointB=home)
        send_email(sub, departure_report, return_report)


def handler(event, context):
    send_notifications()
