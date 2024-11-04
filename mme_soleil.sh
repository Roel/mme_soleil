#!/bin/bash

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

source /opt/mme_soleil/venv/bin/activate

set -a
source /opt/mme_soleil/environment.env
set +a

hypercorn --bind 0.0.0.0:8001 /opt/mme_soleil/mme_soleil/main.py:app