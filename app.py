# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import signal
import sys
from types import FrameType
import os
import requests

from kbb import Kbb


from flask import Flask, request

from utils.logging import logger

app = Flask(__name__)

#Set kbb api key environment variable if it doesn't exist yet (running locally)
if not "kbb_api_key" in os.environ:
    import yaml
    with open("env.yaml") as y:
        env = yaml.load(y, Loader=yaml.FullLoader)
        os.environ["kbb_api_key"] = env['kbb_api_key']

@app.route("/", methods=["POST"])
def run() -> str:
    data = request.get_json()

    vin = data["vin"]
    mileage = data["mileage"]
    zipCode = data["zip"]
    make = data["make"]
    model = data["model"]
    year = data["year"]
    trim = data["trim"]

    kbb = Kbb(os.environ["kbb_api_key"])
    # try:
    #     return kbb.getValueByVin(vin, mileage, zipCode)
    # except Exception as e:
    #     return str(e)
    errors = []
    values = []
    modelMatchesVin = False

    if vin:
        try:
            values = kbb.getValueByVin(vin, mileage, zipCode)
        except Exception as e:
            errors.append(str(e))
        try:
            modelMatchesVin = kbb.compareVehicleVinAndName(vin, year, make, model, trim)
        except Exception as e:
            errors.append(str(e))
    else:
        try:
            values = kbb.getValueByName(year, make, model, trim, mileage, zipCode)
        except Exception as e:
            errors.append(str(e))

    return {"modelMatchesVin": modelMatchesVin, "errors": errors, "values": values}
    

# def kbb_test_call(vin):
#     params = dict()
#     params["api_key"] = os.environ["kbb_api_key"]
#     params["VehicleClass"] = "UsedCar"
#     r = requests.get(config.KBB_API_ENDPOINT + config.KBB_VIN_ENDPOINT + vin, params=params)
#     response = r.json()
#     return response



def shutdown_handler(signal_int: int, frame: FrameType) -> None:
    logger.info(f"Caught Signal {signal.strsignal(signal_int)}")

    from utils.logging import flush

    flush()

    # Safely exit program
    sys.exit(0)


if __name__ == "__main__":
    # Running application locally, outside of a Google Cloud Environment

    # handles Ctrl-C termination
    signal.signal(signal.SIGINT, shutdown_handler)

    app.run(host="localhost", port=8080, debug=True)
else:
    # handles Cloud Run container termination
    signal.signal(signal.SIGTERM, shutdown_handler)
