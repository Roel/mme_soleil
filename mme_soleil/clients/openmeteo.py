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

import pandas as pd


class OpenMeteoClient:
    def __init__(self, app):
        self.app = app

    async def get_weather(self, lat, lon, start_date, end_date):
        meteo = await self.app.httpx.get(
            'https://api.open-meteo.com/v1/dwd-icon',
            params={
                'latitude': lat,
                'longitude': lon,
                'hourly': ','.join([
                    'temperature_2m',
                    'windspeed_10m',
                ]),
                'minutely_15': ','.join([
                    'shortwave_radiation',  # ghi
                    'direct_normal_irradiance',  # dni
                    'diffuse_radiation',  # dhi
                ]),
                'timezone': 'Europe/Brussels',
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d')
            }
        )
        return meteo.json()

    async def get_weather_df(self, lat, lon, start_date, end_date):
        meteo = await self.get_weather(lat, lon, start_date, end_date)

        meteo_df_60m = pd.DataFrame.from_dict(
            meteo['hourly']
        )
        meteo_df_60m.columns = ['time', 'temp_air', 'wind_speed']
        meteo_df_60m.time = pd.to_datetime(
            meteo_df_60m.time, format="%Y-%m-%dT%H:%M")
        meteo_df_60m = meteo_df_60m.set_index('time')
        meteo_df_60m = meteo_df_60m.tz_localize(
            'Europe/Brussels', ambiguous='NaT', nonexistent='NaT')
        # remove NaTs from DST switch
        meteo_df_60m = meteo_df_60m[meteo_df_60m.index.notnull()]

        meteo_df_15m = pd.DataFrame.from_dict(
            meteo['minutely_15']
        )
        meteo_df_15m.columns = ['time', 'ghi', 'dni', 'dhi']
        meteo_df_15m.time = pd.to_datetime(
            meteo_df_15m.time, format="%Y-%m-%dT%H:%M")

        # ghi, dni and dhi are given as mean value over the preceding 15 minutes
        # to get an instant value we take the mean of the preceding 15 minutes and the following 15 minutes
        meteo_df_15m['ghi'] = (
            meteo_df_15m.ghi.shift(-1).fillna(0) + meteo_df_15m.ghi)/2
        meteo_df_15m['dni'] = (
            meteo_df_15m.dni.shift(-1).fillna(0) + meteo_df_15m.dni)/2
        meteo_df_15m['dhi'] = (
            meteo_df_15m.dhi.shift(-1).fillna(0) + meteo_df_15m.dhi)/2

        meteo_df_15m = meteo_df_15m.set_index('time')
        meteo_df_15m = meteo_df_15m.tz_localize(
            'Europe/Brussels', ambiguous='NaT', nonexistent='NaT')
        # remove NaTs from DST switch
        meteo_df_15m = meteo_df_15m[meteo_df_15m.index.notnull()]

        meteo_df = pd.merge(
            left=meteo_df_60m.resample('5T').interpolate('pchip'),
            right=meteo_df_15m.resample('5T').interpolate('pchip'),
            left_index=True,
            right_index=True
        )
        return meteo_df
