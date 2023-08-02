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
import threading
from queue import Queue

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

#GLOBAL VARIABLES
dataReader = VehicleDataReader()
records = {}
count: int
matchedCount: int
errorsCount: int
noTrimMatch: int
totalCalls: int
reporting = False
pricing = True
threadLock = threading.Lock()
limit = float("inf")
remainingCalls = float("inf")
threads: int

#MAIN FUNCTION
@app.route("/", methods=["POST"])
def run() -> str:
    global limit
    global pricing
    global reporting
    global records
    global validation
    global remainingCalls
    global threads

    global count
    global errorsCount
    global matchedCount
    global noTrimMatch
    global totalCalls

    global work

    #Reset variables
    records = {}
    count = 0
    matchedCount = 0
    errorsCount = 0
    totalCalls = 0
    noTrimMatch = 0

    vehicleCount = 0

    #limit used to cap the max number of calls
    limit = request.args.get('limit', default=float("inf"), type = float)
    #report used to flag whether or not to generate a detailed report
    report = request.args.get('report', default="N", type = str)
    #prices used to denote whether to return prices (better off for debugging)
    prices = request.args.get('prices', default = "Y", type = str)
    #Set how many threads to run
    threads = request.args.get('threads', default = 5, type = int)
    #validation is used to denote what validation mode to use.
    #mode 1: VIN or YMM
    #mode 2: VIN, YMM, mileage
    #mode 3: VIN, YMM, mileage, trim
    #mode 4: VIN, YMM mileage, trim, options
    validation = request.args.get('validation', default = 3, type = int)

    dataReader = VehicleDataReader(validation, limit)

    pricing = True if prices == 'Y' else False

    reporting = True if report == 'Y' else False

    if request.is_json:
        data = request.get_json()
        records = dataReader.jsonInput(data)
    else:
        csv = request.get_data().decode()
        records = dataReader.csvInput(str(csv))

    vehicleCount = len(records.keys())
    #----Value Vehicles-------------------------------

    for record in records.values():
        work.put(record)
    
    for i in range(threads-1):
        thread = threading.Thread(target=worker)
        thread.daemon = True
        thread.start()
    
    #Wait for threads to finish
    work.join()

    ret = {"vehicleCount": vehicleCount, "processed": count, "priced": matchedCount, "errors": errorsCount, "totalCallsMade": totalCalls, "remainingCalls": remainingCalls, "usedLowestPricedTrim":noTrimMatch, "vehicles": records}

    return ret

work = Queue()

def worker():
    while True:
        vehicle = work.get()
        try:
            job(vehicle)
        except Exception as e:
            print(e)
        work.task_done()

#THREADED JOB
def job(record):
    global records
    global threadLock
    global reporting
    global validation
    
    global count
    global errorsCount
    global matchedCount
    global noTrimMatch
    global totalCalls

    kbb = Kbb(os.environ["kbb_api_key"], reporting)
    errors = []
    report = {}
    # if float(errorsCount) > float(count) * 0.2: #If there is more than 20% error stop trying
    #     return
    with threadLock:
        count+=1
    try:
        if dataReader.ERRORS in record:
            raise Exception(str(record[dataReader.ERRORS]))
        report = kbb.getVehicleValue(record.get(dataReader.ID), record.get(dataReader.VIN), record.get(dataReader.YEAR), record.get(dataReader.MAKE), record.get(dataReader.MODEL), record.get(dataReader.TRIM),  record.get(dataReader.MILEAGE), "96819", record.get(dataReader.OPTIONS, set()))
        records[record.get(dataReader.ID)]["report"] = {}
        if "prices" in report and report["prices"]:
            with threadLock:
                matchedCount+=1
            prices = report.pop("prices")
            if pricing:
                records[record.get(dataReader.ID)]["prices"] = prices
        if "usedLowestPricedTrim" in report and report["usedLowestPricedTrim"]:
            with threadLock:
                noTrimMatch+=1
        if "numCallsMade" in report:
            with threadLock:
                totalCalls+=report["numCallsMade"]
        records[record.get(dataReader.ID)]["report"] = report
    except Exception as e:
        report = {"errors": [str(e)]}
    if "errors" in report:
        errors = errors + report.pop("errors")
        if len(errors) > 0:
            with threadLock:
                errorsCount+=len(errors)
            records[record.get(dataReader.ID)]["errors"] = errors
    updateRemainingCalls(int(kbb.rateLimit))

def updateRemainingCalls(remaining):
    global remainingCalls
    with threadLock:
        if remaining < remainingCalls:
            remainingCalls = remaining

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
