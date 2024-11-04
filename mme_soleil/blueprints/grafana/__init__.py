# Madame Soleil: solar power production prediction service
# Copyright (C) 2023-2024  Roel Huybrechts

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import datetime
import pytz

from quart import Blueprint, request, current_app as app
from quart_auth import basic_auth_required

grafana = Blueprint('grafana', __name__)


def get_range(data):
    date_from = pytz.utc.localize(datetime.datetime.strptime(
        data['range']['from'][:-5], '%Y-%m-%dT%H:%M:%S')).astimezone(pytz.timezone('Europe/Brussels'))

    date_to = pytz.utc.localize(datetime.datetime.strptime(
        data['range']['to'][:-5], '%Y-%m-%dT%H:%M:%S')).astimezone(pytz.timezone('Europe/Brussels'))

    return date_from, date_to


def get_targets(data):
    return [i['target'] for i in data['targets']]


@grafana.get("/")
@basic_auth_required()
async def test_connection():
    return {'status': 'ok'}, 200


@grafana.post("/metrics")
@basic_auth_required()
async def get_metrics():
    return [
        {"label": "AC power (W)", "value": "AC_W"},
        {"label": "Daily cumulative production (kWh)",
         "value": "daily_kwh_cum"},
        {"label": "Hourly production (kWh)", "value": "hourly_kwh"},
        {"label": "Future daily production (kWh)", "value": "future_daily_kwh"}
    ]


@grafana.post("/metric-payload-options")
@basic_auth_required()
async def get_metric_payload_options():
    return []


@grafana.post("/query")
@basic_auth_required()
async def query():
    data = await request.json
    # print(data)

    date_from, date_to = get_range(data)
    targets = get_targets(data)

    date_from = date_from - datetime.timedelta(minutes=10)
    date_to = date_to + datetime.timedelta(minutes=10)

    result = []

    for t in targets:
        if t == 'AC_W':
            ac_w = await app.services.solar.get_ac_power(date_from, date_to)

            datapoints = []
            for i in ac_w.iterrows():
                timestamp = int(i[0].strftime('%s'))*1000
                value = i[1].ac_W
                datapoints.append([value, timestamp])

            result.append({
                'target': 'AC_W',
                'datapoints': datapoints
            })
        elif t == 'daily_kwh_cum':
            daily_kwh_cum = await app.services.solar.get_daily_cumulative_kwh(date_from, date_to)

            datapoints = []
            for i in daily_kwh_cum.iterrows():
                timestamp = int(i[0].strftime('%s'))*1000
                value = i[1].ac_daily_kWh_cum
                datapoints.append([value, timestamp])

            result.append({
                'target': 'daily_kwh_cum',
                'datapoints': datapoints
            })
        elif t == 'hourly_kwh':
            date_from, date_to = get_range(data)
            date_from = datetime.datetime(
                date_from.year, date_from.month, date_from.day, 0, 0, 0)
            date_to = datetime.datetime(
                date_to.year, date_to.month, date_to.day, 23, 59, 59)
            hourly_kwh = await app.services.solar.get_hourly_production_kwh(date_from, date_to)

            datapoints = []
            for i in hourly_kwh.iterrows():
                timestamp = int(i[0].strftime('%s'))*1000
                value = i[1].ac_hourly_kWh
                datapoints.append([value, timestamp])

            result.append({
                'target': 'hourly_kwh',
                'datapoints': datapoints
            })
        elif t == 'future_daily_kwh':
            today = datetime.date.today()
            date_from = datetime.datetime(
                today.year, today.month, today.day, 0, 0, 0)
            date_to = datetime.datetime(
                date_from.year, date_from.month, date_from.day, 23, 59, 59) + datetime.timedelta(days=2)

            daily_kwh = await app.services.solar.get_daily_production_kwh(date_from, date_to)

            datapoints = []
            for i in daily_kwh.iterrows():
                timestamp = int(i[0].strftime('%s'))*1000
                value = i[1].ac_daily_kWh
                datapoints.append([value, timestamp])

            result.append({
                'target': 'future_daily_kwh',
                'datapoints': datapoints
            })

    return result
