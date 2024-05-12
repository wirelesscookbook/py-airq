#!/usr/bin/python
'''
Nova SDS011 sensor Python parser and InfluxDB writer
A Python module that reads SDS011 sensor data to an InfluxDB instance.
Author: @billz <billzimmerman@gmail.com>
Author URI: https://github.com/billz/
License: GNU General Public License v3.0
License URI: https://github.com/wificookbook/py-airq/blob/master/LICENSE

This project is forked from and generally inspired by:

    https://github.com/jessedc/sds011-pm-sensor-python
    https://github.com/ikalchev/py-sds011
    https://github.com/xtai/py-influx-air

This is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
'''

"""CLI Entry point"""
import argparse
import time

from influxdb import InfluxDBClient
from datetime import datetime, timezone

#from Adafruit_IO import Client
#ADAFRUIT_AIO_USERNAME = "my-aio-username"
#ADAFRUIT_AIO_KEY      = "my-aio-key"
#aio = Client(ADAFRUIT_AIO_USERNAME, ADAFRUIT_AIO_KEY)

from . import SDS011

influx_client = None
influx_db = None

def main():
    """Invoke the parser"""

    parser = argparse.ArgumentParser(description='Parse sds011 sensor data to an InfluxDB instance.')
    parser.add_argument('-p', '--port', help='SDS011 serial port', default='/dev/ttyS0')
    parser.add_argument('-i', '--influx', help='InfluxDB host', default='localhost')
    parser.add_argument('-d', '--database', help='InfluxDB database', default='pistation')
    parser.add_argument('-s', '--sds011_measurement', help='InfluxDB measurement for sds011 data', default='aq')
    parser.add_argument('-l', '--location', help='InfluxDB tag for location', default='home')
    parser.add_argument('-g', '--geohash', help='InfluxDB tag for geohash', default='gbsuv7s')
    parser.add_argument('-w', '--warmup', help='Warmup period for sds011, in seconds', type=int, default=20)
    parser.add_argument('-v', '--interval', help='Sample interval for sds011, in seconds', type=int, default=60)
    args = parser.parse_args()

    global influx_db, influx_client
    influx_client = InfluxDBClient(host=args.influx, port=8086)
    influx_db = args.database

    sds011_measurement = args.sds011_measurement
    location = args.location
    geohash = args.geohash
    warmup = args.warmup
    interval = args.interval

    # Connect to sds011 via port, default: /dev/ttyS0
    sensor011 = SDS011.SDS011(args.port, use_query_mode=True)

    print("Warming up SDS011...")

    try:
        while True:
            # 0 sec - warm-up sds011
            sensor011.sleep(sleep=False)
     
            # 0 sec - warm-up bme680, while waiting for sds011 to wake up
            for i in range(warmup):
                time.sleep(1)
           
            # begin reading from sds011
            results = []
            ts = datetime.now(timezone.utc).astimezone().isoformat()
            result = sensor011.query()
            if result is not None:
                pm25, pm100 = result
                measurement = measurement_from_sds011(ts, sds011_measurement, pm25, pm100, geohash, location)
                results.append(measurement)
                print("SDS011: PM2.5 {}; PM10 {}".format(pm25, pm100))
            else:
                print("No response from SDS011 sensor")
            sensor011.sleep()

            # write sds011 results to InfluxDB
            influx_client.write_points(results, database=influx_db)

            # set up location metadata
            #location_meta = {
            #    "lat": 64.1334735,
            #    "lon": -21.922653,
            #    "ele": 12,
            #    "created_at": ts
            }

            # send sds011 results to Adafruit IO
            #aio.send('pistation25',pm25,location_meta)
            #aio.send('pistation10',pm100,location_meta)

            # warmup secs
            time.sleep(interval - warmup)

    except KeyboardInterrupt:
        print("Pushing sensor into sleep state...")
        sensor011.sleep()
        print("Done.")

def measurement_from_sds011(timestamp, measurement, pm25, pm100, geohash, location):
    """Turn the SDS011 object into a set of influx-db compatible measurement object"""

    return {
        "measurement": str(measurement),
        "tags": {
            "sensor": "sds011",
            "location": str(location),
            "geohash": str(geohash),
        },
        "time": timestamp,
        "fields": {
            "pm25": float(pm25),
            "pm100": float(pm100)
        }
    }

if __name__ == "__main__":
    main()
