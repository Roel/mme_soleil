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

from dataclasses import dataclass
import datetime

import pytz
from clients.openmeteo import OpenMeteoClient

import pandas as pd


@dataclass
class TimePeriodStatsDto:
    start: datetime.datetime
    end: datetime.datetime
    unit: str
    q25: float
    q50: float
    q75: float
    stddev: float


_PD_TIMEFORMAT = '%Y-%m-%d %H:%M:%S'


class WeatherService:
    def __init__(self, app):
        self.app = app

        self.open_meteo_client = OpenMeteoClient(self.app)

        self.weather_df = None

    async def get_weather(self, start_date, end_date):
        meteo_df = await self.open_meteo_client.get_weather_df(
            self.app.services.solar.get_location().latitude,
            self.app.services.solar.get_location().longitude,
            start_date=start_date,
            end_date=end_date
        )

        self.weather_df = meteo_df
        return meteo_df

    async def get_temperature_stats(self, start, end):
        if self.weather_df is None:
            raise RuntimeError

        df_temp = pd.DataFrame(self.weather_df.temp_air)
        df_temp = df_temp[start.strftime(
            _PD_TIMEFORMAT): end.strftime(_PD_TIMEFORMAT)]

        df_temp['time'] = pd.to_datetime(df_temp.index)

        if len(df_temp) == 0:
            return None

        return TimePeriodStatsDto(
            start=df_temp.time.min().astimezone(pytz.timezone('Europe/Brussels')),
            end=df_temp.time.max().astimezone(pytz.timezone('Europe/Brussels')),
            unit='° C',
            q25=df_temp.temp_air.quantile(0.25),
            q50=df_temp.temp_air.quantile(0.5),
            q75=df_temp.temp_air.quantile(0.75),
            stddev=df_temp.temp_air.std()
        )
