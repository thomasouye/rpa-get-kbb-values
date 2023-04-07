import io
import csv
class VehicleDataReader:
    VIN = "vin"
    YEAR = "year"
    MAKE = "make"
    MODEL = "model"
    TRIM = "trim"
    MILEAGE = "mileage"
    ZIP = "zip"
    OPTIONS = "options"

    CSV_VIN_COLUMN = "VIN"
    CSV_YEAR_COLUMN = "YEAR"
    CSV_MAKE_COLUMN = "MakeName"
    CSV_MODEL_COLUMN = "ModelName"
    CSV_TRIM_COLUMN = "BodyStyle"
    CSV_OPTION_COLUMN = "OptionDescription"
    CSV_MILEAGE_COLUMN = ""


    def __init__(self) -> None:
        self.vehicleData = {}

    def csvInput(self, csvData):
        csvReader = csv.DictReader(io.StringIO(csvData))
        for row in csvReader:
            vin = row.pop(self.CSV_VIN_COLUMN, None)
            year = row.pop(self.CSV_YEAR_COLUMN, None)
            make = row.pop(self.CSV_MAKE_COLUMN, None)
            model = row.pop(self.CSV_MODEL_COLUMN, None)
            trim = row.pop(self.CSV_TRIM_COLUMN, None)
            mileage = row.pop(self.CSV_MILEAGE_COLUMN, None)

            if mileage and mileage.isdigit():
                mileage = int(mileage)


            option = row.pop(self.CSV_OPTION_COLUMN, None)
            
            if vin not in self.vehicleData:
                options = set()
                options.add(option)
                vehicle = {self.VIN: vin, 
                           self.YEAR: year, 
                           self.MAKE: make, 
                           self.MODEL: model, 
                           self.TRIM: model + ' ' + trim, 
                           self.MILEAGE: mileage, 
                           self.OPTIONS: options}
                self.vehicleData[vin] = vehicle
            else:
                self.vehicleData[vin]["options"].add(option)
        return self.vehicleData.values()
