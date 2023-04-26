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

from kbb import Kbb
from vehicledatareader import VehicleDataReader


from flask import Flask, request

from utils.logging import logger

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

#Set kbb api key environment variable if it doesn't exist yet (running locally)
if not "kbb_api_key" in os.environ:
    import yaml
    with open("env.yaml") as y:
        env = yaml.load(y, Loader=yaml.FullLoader)
        os.environ["kbb_api_key"] = env['kbb_api_key']

@app.route("/", methods=["POST"])
def run() -> str:
    #limit used to cap the max number of calls
    limit = request.args.get('limit', default=float("inf"), type = float)
    #report used to flag whether or not to generate a detailed report
    report = request.args.get('report', default="N", type = str)
    #prices used to denote whether to return prices (better off for debugging)
    prices = request.args.get('prices', default = "Y", type = str)
    #validation is used to denote what validation mode to use.
    #mode 1: VIN or YMM
    #mode 2: VIN, YMM, mileage
    #mode 3: VIN, YMM, mileage, trim
    #mode 4: VIN, YMM mileage, trim, options
    validation = request.args.get('validation', default = 3, type = int)

    pricing = True if prices == 'Y' else False
    reporting = True if report == 'Y' else False

    kbb = Kbb(os.environ["kbb_api_key"], reporting)

    dataReader = VehicleDataReader(validation)
    if request.is_json:
        data = request.get_json()
        records = dataReader.jsonInput(data)
    else:
        csv = request.get_data().decode()
        records = dataReader.csvInput(str(csv))

    #----Value Vehicles-------------------------------
    values = []
    count = 0
    matched = 0
    errors = 0
    notrimmatch = 0
    totalCalls = 0

    for record in records:
        count+=1
        try:
            if dataReader.ERRORS in record:
                raise Exception(str(record[dataReader.ERRORS]))
            report = kbb.getVehicleValue(record.get(dataReader.ID, count), record.get(dataReader.VIN), record.get(dataReader.YEAR), record.get(dataReader.MAKE), record.get(dataReader.MODEL), record.get(dataReader.TRIM),  record.get(dataReader.MILEAGE), "96819", record.get(dataReader.OPTIONS, set()))
            if "prices" in report:
                matched+=1
                if not pricing:
                    report.pop("prices")
            if "usedLowestPricedTrim" in report and report["usedLowestPricedTrim"]:
                notrimmatch+=1
            if "numCallsMade" in report:
                totalCalls+=report["numCallsMade"]
        except Exception as e:
            error = []
            error.append(str(e))
            report = {"vin": record.get(dataReader.VIN), 
                      "year": record.get(dataReader.YEAR), 
                      "make": record.get(dataReader.MAKE), 
                      "model": record.get(dataReader.MODEL), 
                      "trim": record.get(dataReader.TRIM), 
                      "errors": error}
            raise e
        if "errors" in report:
            errors+=len(report["errors"])
        values.append(report)
        if count == limit: #If we hit the limit, stop
            break
        if float(errors) > float(count) * 0.2: #If there is more than 20% error stop trying
            break
    
    ret = {"count": count, "matched": matched, "errors": errors, "totalCallsMade": totalCalls, "remainingCalls": kbb.rateLimit, "usedLowestPricedTrim":notrimmatch, "values": values}

    return ret

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
