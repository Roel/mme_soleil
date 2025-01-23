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

import os


@dataclass
class SolarInverter:
    Name: str = 'Huawei SUN2000-4.6KTL-L1'
    Vac: int = 240
    Pso: float = 1
    Paco: float = 5000.0
    Pdco: float = 5059.411133
    Vdco: float = 360.0
    C0: float = -0.000002
    C1: float = 0.000021
    C2: float = 0.000814
    C3: float = -0.000727
    Pnt: float = 1.5
    Vdcmax: float = 600.0
    Idcmax: float = 12.5
    Mppt_low: float = 90.0
    Mppt_high: float = 560.0


@dataclass
class SolarPanel:
    Name: str = 'Hyundai HiE-S400VG'
    Technology: str = 'Mono-c-Si'
    STC: float = 400.0
    PTC: float = 364.0
    A_c: float = 2.02
    N_s: float = 340.0
    I_sc_ref: float = 10.97
    V_oc_ref: float = 46.4
    I_mp_ref: float = 10.36
    V_mp_ref: float = 38.6
    alpha_sc: float = 0.004215
    beta_oc: float = -0.164485
    T_NOCT: float = 45.4
    a_ref: float = 2.059511
    I_L_ref: float = 10.385126
    I_o_ref: float = 4.5757e-10
    R_s: float = 0.218704
    R_sh_ref: float = 976.143086
    Adjust: float = 9.872948
    gamma_r: float = -0.34
    BIPV: str = 'N'


class Config:
    QUART_AUTH_MODE = 'bearer'
    QUART_AUTH_BASIC_USERNAME = 'admin'
    QUART_AUTH_BASIC_PASSWORD = os.environ.get('API_ADMIN_PASS')

    LOCATION_LAT = float(os.environ.get('LOCATION_LAT'))
    LOCATION_LON = float(os.environ.get('LOCATION_LON'))
    LOCATION_ALTITUDE = float(os.environ.get('LOCATION_ALTITUDE'))
    LOCATION_TIMEZONE = os.environ.get('LOCATION_TIMEZONE')

    SOLAR_PANEL = SolarPanel()
    SOLAR_INVERTER = SolarInverter()

    SOLAR_ARRAY1_TILT = int(os.environ.get('SOLAR_ARRAY1_TILT'))
    SOLAR_ARRAY1_AZIMUTH = int(os.environ.get('SOLAR_ARRAY1_AZIMUTH'))
    SOLAR_ARRAY1_HEIGHT = int(os.environ.get('SOLAR_ARRAY1_HEIGHT'))
    SOLAR_ARRAY1_MODULECOUNT = int(os.environ.get('SOLAR_ARRAY1_MODULECOUNT'))

    SOLAR_ARRAY2_TILT = int(os.environ.get('SOLAR_ARRAY2_TILT'))
    SOLAR_ARRAY2_AZIMUTH = int(os.environ.get('SOLAR_ARRAY2_AZIMUTH'))
    SOLAR_ARRAY2_HEIGHT = int(os.environ.get('SOLAR_ARRAY2_HEIGHT'))
    SOLAR_ARRAY2_MODULECOUNT = int(os.environ.get('SOLAR_ARRAY2_MODULECOUNT'))
