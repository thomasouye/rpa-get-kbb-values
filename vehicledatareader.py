import io
import csv
class VehicleDataReader:
    def __init__(self, csvData) -> None:
        csvReader = csv.DictReader(io.StringIO(csvData))
        self.vehicleData = {}
        for row in csvReader:
            option = row.pop("OptionDescription", None)
            if row["VIN"] not in self.vehicleData:
                row["options"] = set()
                row["options"].add(option)
                self.vehicleData[row["VIN"]] = row
            else:
                self.vehicleData[row["VIN"]]["options"].add(option)

    def getVehicleData(self):
        return self.vehicleData