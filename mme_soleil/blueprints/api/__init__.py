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
from quart import Blueprint, request, current_app as app
from quart_auth import basic_auth_required

api = Blueprint('api', __name__)

TYPEFN_DATETIME = datetime.datetime.fromisoformat
TYPEFN_DATE = datetime.date.fromisoformat
def TYPEFN_TIMEDELTA_H(x): return datetime.timedelta(hours=int(x))


@api.get("/production/peak")
@basic_auth_required()
async def get_production_peak():
    errors = []

    start = request.args.get(
        'start', default=datetime.datetime.now(), type=TYPEFN_DATETIME)
    end = request.args.get('end', type=TYPEFN_DATETIME)
    if end is None:
        errors.append('Failed to parse value for parameter: end.')

    if end is not None and end <= start:
        errors.append('Validation error: end should be greater than start.')

    min_kwh = request.args.get('min_kwh', type=float)
    min_temp = request.args.get('min_temp', type=float)

    precision = request.args.get('precision', type=int)
    if precision is None:
        errors.append('Failed to parse value for parameter: precision.')

    peak_duration = request.args.get(
        'peak_duration_h', type=TYPEFN_TIMEDELTA_H)
    if peak_duration is None:
        errors.append('Failed to parse value for parameter: peak_duration_h.')

    order = request.args.get('order', type=str)
    if order not in ['first', 'last']:
        errors.append(
            'Failed to parse value for parameter: order. Should be "first" or "last".')

    if len(errors) == 0:
        result = await app.services.solar.get_production_peak(
            end=end, peak_duration=peak_duration, order=order,
            precision=precision, start=start, min_kwh=min_kwh,
            min_temp=min_temp
        )
        return {'status': 'ok',
                'result': result.isoformat()}
    else:
        return {'status': 'error',
                'errors': errors}, 400


@api.get("/production/bounds")
@basic_auth_required()
async def get_production_bounds():
    errors = []

    date = request.args.get(
        'date', default=datetime.date.today(), type=TYPEFN_DATE)
    if date is None:
        errors.append('Failed to parse value for parameter: date.')

    min_kw = request.args.get('min_kW', default=0, type=float)
    if min_kw is None:
        errors.append('Failed to parse value for parameter: min_kw.')

    if len(errors) == 0:
        start, end = await app.services.solar.get_production_bounds(
            date=date, min_kw=min_kw
        )
        return {'status': 'ok',
                'start': start.isoformat() if start is not None else None,
                'end': end.isoformat() if start is not None else None}
    else:
        return {'status': 'error',
                'errors': errors}, 400


@api.get("/production/weather")
@basic_auth_required()
async def get_production_weather():
    errors = []

    start = request.args.get(
        'start', default=datetime.datetime.now(), type=TYPEFN_DATETIME)
    end = request.args.get('end', type=TYPEFN_DATETIME)
    if end is None:
        errors.append('Failed to parse value for parameter: end.')

    if end is not None and end <= start:
        errors.append('Validation error: end should be greater than start.')

    if len(errors) == 0:
        data = await app.services.solar.get_production_weather(
            start_date=start, end_date=end
        )
        return {'status': 'ok',
                'weather_data': data['weather_data'],
                'clearsky': data['clearsky'],
                'ratio': data['ratio']}
    else:
        return {'status': 'error',
                'errors': errors}, 400


@api.get("/production/daily")
@basic_auth_required()
async def get_daily_cumulative_production():
    errors = []

    default_start = datetime.datetime.combine(
        datetime.date.today(), datetime.time(0, 0, 0))

    start = request.args.get(
        'start', default=default_start, type=TYPEFN_DATETIME)
    end = request.args.get(
        'end', default=datetime.datetime.now(), type=TYPEFN_DATETIME)
    if end is None:
        errors.append('Failed to parse value for parameter: end.')

    if end is not None and end <= start:
        errors.append('Validation error: end should be greater than start.')

    if len(errors) == 0:
        data = await app.services.solar.get_daily_cumulative_kwh(
            start=start, end=end
        )
        return {'status': 'ok',
                'production': data['ac_daily_kWh_cum'].max(),
                'unit': 'kWh'}
    else:
        return {'status': 'error',
                'errors': errors}, 400


@api.get("/temperature/stats")
@basic_auth_required()
async def get_temperature_stats():
    errors = []

    start = request.args.get(
        'start', default=datetime.datetime.now(), type=TYPEFN_DATETIME)
    end = request.args.get('end', type=TYPEFN_DATETIME)
    if end is None:
        errors.append('Failed to parse value for parameter: end.')

    if end is not None and end <= start:
        errors.append('Validation error: end should be greater than start.')

    if len(errors) == 0:
        result = await app.services.weather.get_temperature_stats(start, end)

        if result is not None:
            return {
                'start': result.start.isoformat(),
                'end': result.end.isoformat(),
                'unit': result.unit,
                'q25': result.q25,
                'q50': result.q50,
                'q75': result.q75,
                'stddev': result.stddev
            }
        else:
            errors.append('No data was found for your request period.')

    return {'status': 'error',
            'errors': errors}, 400
