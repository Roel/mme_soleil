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

import copy
import datetime
from enum import Enum
from httpx import HTTPError
import pandas as pd
import pvlib

from pvlib.location import Location
from pvlib.pvsystem import Array, FixedMount, PVSystem
from pvlib.modelchain import ModelChain

_PD_TIMEFORMAT = '%Y-%m-%d %H:%M:%S'


class ModelResults(Enum):
    UNDEFINED = 1


class SolarService:
    def __init__(self, app):
        self.app = app

        self.location = Location(
            latitude=self.app.config['LOCATION_LAT'],
            longitude=self.app.config['LOCATION_LON'],
            tz=self.app.config['LOCATION_TIMEZONE'],
            altitude=self.app.config['LOCATION_ALTITUDE']
        )

        self.temperature_model = pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS[
            'sapm']['close_mount_glass_glass']
        self.solarpanel_parameters = pd.Series(
            dict(self.app.config['SOLAR_PANEL'].__dict__))
        self.inverter_parameters = pd.Series(
            dict(self.app.config['SOLAR_INVERTER'].__dict__))

        self.system = PVSystem(
            arrays=[
                Array(
                    mount=FixedMount(
                        surface_tilt=self.app.config['SOLAR_ARRAY1_TILT'],
                        surface_azimuth=self.app.config['SOLAR_ARRAY1_AZIMUTH'],
                        racking_model='close_mount',
                        module_height=self.app.config['SOLAR_ARRAY1_HEIGHT']
                    ),
                    module_parameters=self.solarpanel_parameters,
                    strings=1,
                    modules_per_string=self.app.config['SOLAR_ARRAY1_MODULECOUNT'],
                    temperature_model_parameters=self.temperature_model
                ),
                Array(
                    mount=FixedMount(
                        surface_tilt=self.app.config['SOLAR_ARRAY2_TILT'],
                        surface_azimuth=self.app.config['SOLAR_ARRAY2_AZIMUTH'],
                        racking_model='close_mount',
                        module_height=self.app.config['SOLAR_ARRAY2_HEIGHT']
                    ),
                    module_parameters=self.solarpanel_parameters,
                    strings=1,
                    modules_per_string=self.app.config['SOLAR_ARRAY2_MODULECOUNT'],
                    temperature_model_parameters=self.temperature_model
                )
            ],
            inverter_parameters=self.inverter_parameters
        )

        self.model = ModelChain(
            system=self.system,
            location=self.location,
            aoi_model='ashrae',
            spectral_model='no_loss',
            temperature_model='sapm'
        )

        self.model_results = ModelResults.UNDEFINED
        self.model_results_clearsky = ModelResults.UNDEFINED
        self.weather = None

        self.__scheduled_jobs()

    def get_location(self):
        return self.location

    async def run_model(self, start_date=None, end_date=None):
        if start_date is None:
            start_date = datetime.date.today()

        if end_date is None:
            end_date = start_date + datetime.timedelta(days=3)

        if end_date < start_date:
            raise ValueError(
                'end_date should be greater than or equal to start_date')

        # clear sky
        period = pd.date_range(start_date, end_date,
                               freq='5min', tz='Europe/Brussels')
        clearsky = self.get_location().get_clearsky(period, model='simplified_solis')
        self.model_results_clearsky = copy.deepcopy(
            self.model.run_model(clearsky).results)

        # using weather data
        try:
            self.weather = await self.app.services.weather.get_weather(start_date, end_date)
            self.model_results = copy.deepcopy(
                self.model.run_model(self.weather).results)
        except HTTPError:
            pass

    async def get_ac_power(self, start, end, model_results=None):
        if model_results is None:
            model_results = self.model_results

        if model_results is ModelResults.UNDEFINED:
            raise RuntimeError

        df_ac = pd.DataFrame(model_results.ac)
        df_ac = df_ac.rename(columns={'p_mp': 'ac_W'})
        df_ac.ac_W = df_ac.ac_W.apply(lambda x: min(max(0, x), 5000))

        return df_ac[start.strftime(_PD_TIMEFORMAT): end.strftime(_PD_TIMEFORMAT)]

    async def get_production_wh(self, start, end, model_results=None):
        if model_results is None:
            model_results = self.model_results

        if model_results is ModelResults.UNDEFINED:
            raise RuntimeError

        df_ac = await self.get_ac_power(start, end, model_results)

        # ac_W is the instant value, to calculate production we take the mean power for the interval
        df_ac['ac_W_mean'] = (df_ac.ac_W.shift(-1).fillna(0) + df_ac.ac_W)/2
        df_ac['ac_Wh'] = df_ac.ac_W_mean / (3600 / (5 * 60))

        return df_ac[['ac_Wh']][start.strftime(_PD_TIMEFORMAT): end.strftime(_PD_TIMEFORMAT)]

    async def get_daily_cumulative_kwh(self, start, end):
        start_period = datetime.datetime(
            start.year, start.month, start.day, 0, 0, 0)
        end_period = datetime.datetime(
            end.year, end.month, end.day, 23, 59, 59)

        df_ac = await self.get_production_wh(start_period, end_period)
        df_ac['ac_daily_kWh_cum'] = df_ac.ac_Wh.groupby(
            pd.Grouper(freq='1D')).cumsum() / 1000

        return df_ac[['ac_daily_kWh_cum']][start.strftime(_PD_TIMEFORMAT): end.strftime(_PD_TIMEFORMAT)]

    async def get_hourly_production_kwh(self, start, end):
        start_period = datetime.datetime(
            start.year, start.month, start.day, 0, 0, 0)
        end_period = datetime.datetime(
            end.year, end.month, end.day, 23, 59, 59)

        df_ac = await self.get_production_wh(start_period, end_period)
        df_ac['ac_hourly_kWh'] = df_ac.ac_Wh.groupby(
            pd.Grouper(freq='1h')).sum() / 1000

        return df_ac[['ac_hourly_kWh']][df_ac.ac_hourly_kWh > 0][
            start.strftime(_PD_TIMEFORMAT): end.strftime(_PD_TIMEFORMAT)].dropna()

    async def get_daily_production_kwh(self, start, end):
        start_period = datetime.datetime(
            start.year, start.month, start.day, 0, 0, 0)
        end_period = datetime.datetime(
            end.year, end.month, end.day, 23, 59, 59)

        df_ac = await self.get_production_wh(start_period, end_period)
        df_ac['ac_daily_kWh'] = df_ac.ac_Wh.groupby(
            pd.Grouper(freq='1D')).sum() / 1000

        return df_ac[['ac_daily_kWh']].dropna()

    async def get_production_peak(self, end, peak_duration, order, precision, start=None, min_kwh=None, min_temp=None):
        if order not in ['first', 'last']:
            raise ValueError('order should be "first" or "last"')
        else:
            order = {
                'first': 0,
                'last': -1
            }.get(order)


        if start is None:
            start = datetime.datetime.now()

        if end <= start:
            raise ValueError('end should be greater than start')

        indexer = pd.api.indexers.FixedForwardWindowIndexer(
            window_size=int(peak_duration.total_seconds()//300))

        df_ac = await self.get_production_wh(start, end + peak_duration)
        df_ac = df_ac.merge(self.weather, left_index=True, right_index=True)

        df_ac['ac_kWh_rolling'] = df_ac.ac_Wh.rolling(
            window=indexer).sum() / 1000
        df_ac['temp_air_rolling'] = df_ac.temp_air.rolling(
            window=indexer).mean()

        if min_kwh is not None:
            result = df_ac[df_ac['ac_kWh_rolling'] >= min_kwh].sort_index()
            if result.size > 0 and min_temp is None:
                return result.iloc[order].name.to_pydatetime()
            elif result.size > 0 and min_temp is not None:
                candidate = result.iloc[order]
                if candidate.temp_air < min_temp:
                    candidates_temp = result[result.temp_air >= min_temp]
                    if len(candidates_temp) > 0:
                        candidate = candidates_temp.iloc[order]

                if candidate.temp_air >= min_temp:
                    return candidate.name.to_pydatetime()

        df_ac['ac_kWh_rolling_rounded'] = df_ac.ac_kWh_rolling.round(precision)
        df_ac['temp_air_rolling_rounded'] = df_ac.temp_air_rolling.round(
            precision)

        result_solar = df_ac[df_ac['ac_kWh_rolling_rounded'] ==
                             df_ac['ac_kWh_rolling_rounded'].max()].sort_index()

        result_temp = df_ac[df_ac['temp_air_rolling_rounded'] ==
                            df_ac['temp_air_rolling_rounded'].max()].sort_index()

        candidate_solar = result_solar.iloc[order]
        candidate_temp = result_temp.iloc[order]

        if min_kwh is not None and candidate_solar.ac_kWh_rolling < 0.25 * min_kwh:
            # not sunny, use peak temp

            if min_temp is not None:
                return candidate_temp.name.to_pydatetime()
            else:
                return candidate_solar.name.to_pydatetime()
        elif min_kwh is not None and candidate_solar.ac_kWh_rolling < 0.75 * min_kwh:
            # partially sunny, second peak on temp

            if min_temp is not None:
                result_solar_temp = result_solar[result_solar['temp_air_rolling_rounded'] ==
                                                 result_solar['temp_air_rolling_rounded'].max()].sort_index()
                return result_solar_temp.iloc[order].name.to_pydatetime()
            else:
                return candidate_solar.name.to_pydatetime()
        else:
            # sunny, second peak on temp if too cold

            if min_temp is not None and candidate_solar.temp_air_rolling < min_temp:
                result_solar_temp = result_solar[result_solar['temp_air_rolling_rounded'] ==
                                                 result_solar['temp_air_rolling_rounded'].max()].sort_index()
                if result_solar_temp.size >= 1:
                    return result_solar_temp.iloc[order].name.to_pydatetime()
                else:
                    return candidate_solar.name.to_pydatetime()
            else:
                return candidate_solar.name.to_pydatetime()

    async def get_production_bounds(self, date, min_kw=0):
        start_period = datetime.datetime(
            date.year, date.month, date.day, 0, 0, 0)
        end_period = datetime.datetime(
            date.year, date.month, date.day, 23, 59, 59)

        df_ac = await self.get_ac_power(start_period, end_period)
        result = df_ac[df_ac['ac_W'] > min_kw * 1000].sort_index()

        if result.size > 0:
            start = result.iloc[0].name.to_pydatetime()
            end = result.iloc[-1].name.to_pydatetime()
        else:
            start = end = None

        return start, end

    async def get_production_weather(self, start_date, end_date):
        production_weather = (await self.get_production_wh(
            start_date, end_date, self.model_results)).ac_Wh.sum() / 1000

        production_clearsky = (await self.get_production_wh(
            start_date, end_date, self.model_results_clearsky)).ac_Wh.sum() / 1000

        if production_clearsky == 0:
            ratio = 0
        else:
            ratio = production_weather / production_clearsky

        return {
            'weather_data': production_weather,
            'clearsky': production_clearsky,
            'ratio': ratio
        }

    def __scheduled_jobs(self):
        self.app.scheduler.add_job(self.run_model, 'cron', minute='50')
