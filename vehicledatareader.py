import io
import csv
class VehicleDataReader:
    ID = "id"
    VIN = "vin"
    YEAR = "year"
    MAKE = "make"
    MODEL = "model"
    TRIM = "trim"
    MILEAGE = "mileage"
    ZIP = "zip"
    OPTIONS = "options"

    CSV_ID_COLUMN = "ID"
    CSV_VIN_COLUMN = "VIN"
    CSV_YEAR_COLUMN = "YEAR"
    CSV_MAKE_COLUMN = "MakeName"
    CSV_MODEL_COLUMN = "ModelName"
    CSV_TRIM_COLUMN = "BodyStyle"
    CSV_OPTION_COLUMN = "OptionDescription"
    CSV_MILEAGE_COLUMN = "Mileage"


    def __init__(self) -> None:
        self.vehicleData = {}

    def csvInput(self, csvData):
        csvReader = csv.DictReader(io.StringIO(csvData))
        count = 0
        for row in csvReader:
            count += 1
            id = row.pop(self.CSV_ID_COLUMN, count)
            vin = row.pop(self.CSV_VIN_COLUMN, None)
            year = row.pop(self.CSV_YEAR_COLUMN, None)
            make = row.pop(self.CSV_MAKE_COLUMN, None)
            model = row.pop(self.CSV_MODEL_COLUMN, None)
            trim = row.pop(self.CSV_TRIM_COLUMN, "")
            mileage = row.pop(self.CSV_MILEAGE_COLUMN, None)

            if mileage and mileage.isdigit():
                mileage = int(mileage)

            option = row.pop(self.CSV_OPTION_COLUMN, None)
            
            key = vin if vin else str(id)
            print(key)

            if key not in self.vehicleData:
                print(key)
                options = set()
                if option:
                    options.add(option)
                vehicle = {self.ID: id,
                           self.VIN: vin, 
                           self.YEAR: year, 
                           self.MAKE: make, 
                           self.MODEL: model, 
                           self.TRIM: model + ' ' + trim, 
                           self.MILEAGE: mileage, 
                           self.OPTIONS: options}
                self.vehicleData[key] = vehicle
            else:
                if option:
                    self.vehicleData[key]["options"].add(option)
        print(str(self.vehicleData))
        print(str(self.vehicleData.values()))
        return self.vehicleData.values()
