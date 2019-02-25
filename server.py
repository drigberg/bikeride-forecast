import asyncio
import datetime
import json
import logging
import pathlib
import smtplib
import tornado.httpserver
import tornado.ioloop
import tornado.web
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from lib import create_email_contents, get_secrets, get_weather_data, Subscription, SuckReport

logger = logging.getLogger(__name__)
PORT = 8888


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
    msg.attach( MIMEText(html, 'html'))

    smtp = smtplib.SMTP('smtp.gmail.com', 587)
    smtp.set_debuglevel(0)
    smtp.ehlo()
    smtp.starttls()
    smtp.ehlo()
    smtp.login(from_address, secrets["email_pass"])
    smtp.sendmail(from_address, sub.email, msg.as_string())
    smtp.quit()
    logger.info('Sent email to %s!', sub.email)



async def send_notifications():
    logger.info('Sending notifications!')
    store = pathlib.Path('store.json')
    subscriptions = json.loads(store.read_bytes())
    for subscription_data in subscriptions:
        sub = Subscription.from_data(subscription_data)
        home = tuple(sub.home)
        dest = tuple(sub.dest)
        midway_point = (
            round((home[0] + dest[0]) / 2, 6),
            round((home[1] + dest[1]) / 2, 6)
        )
        weather_data = await get_weather_data(midway_point)
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

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("OK")

class SubscriptionHandler(tornado.web.RequestHandler):
    def post(self):
        logger.info('New subscription received!')
        data = json.loads(self.request.body.decode('utf-8'))
        sub = Subscription.from_data(data)
        store = pathlib.Path('store.json')

        subs = json.loads(store.read_bytes())
        subs.append(sub.to_serializable())
        store.write_bytes(bytes(json.dumps(subs), 'utf-8'))

        # store email, start/end points, travel times
        logger.info("Added subscription for %s <%s>", sub.name, sub.email)
        self.write(f"Added subscription for {sub.name} at {sub.email}!")


async def notification_worker():
    logger.info('Starting notification worker!')
    while True:
        now = datetime.datetime.now()
        if now.hour != 6:
            print(f"Sending notifications at {datetime.datetime.now()}!")
            await send_notifications()
        await asyncio.sleep(3600) # one hour

def task():
    app = tornado.web.Application([
        (r"/", MainHandler),
        (r"/subscription", SubscriptionHandler)
    ])

    logger.info("Starting server on port %d!", PORT)
    server = tornado.httpserver.HTTPServer(app)
    server.listen(PORT)

    event_loop = asyncio.events.get_event_loop()
    event_loop.create_task(notification_worker())
    tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
    task()
