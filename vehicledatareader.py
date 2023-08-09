import io
import csv
from typing import List
from pydantic import BaseModel, ValidationError, validator, root_validator

class Vehicle(BaseModel):
    key: str
    vin: str = ''
    year: int 
    make: str 
    model: str
    trim: str = None
    mileage: int = None
    zip: str = None
    options: List[str] = list()
    validation: int = 3

    def get(self, attribute, default = None):
        value = getattr(self, attribute, None)
        if value:
            return value
        else:
            return default

    @root_validator
    def input_validation_mode(cls, v):
        validation = v.get('validation')
        vin, year, make, model, mileage, trim = v.get('vin'), v.get('year'), v.get('make'), v.get('model'), v.get('mileage'), v.get('trim')
        options = v.get('options')
        if validation == 1:
            assert vin or (year and make and model), 'VIN or year/make/model is required.'
        elif validation == 2:
            assert vin and year and make and model and mileage, 'VIN, year/make/model, and mileage are required.'
        elif validation == 3:
            assert vin and year and make and model and mileage and trim, 'VIN, year/make/model, trim, and mileage are required.'
        elif validation == 4:
            assert vin and year and make and model and mileage and trim and len(options) > 0, 'VIN, year/make/model, trim, mileage, and vehicle options are required.'
        else:
            raise ValueError('Validation mode must be an integer between 1-4.')
        
        return v


    @validator('make', each_item=True)
    def check_make_not_empty(cls, v):
        assert v != '', 'Empty strings are not allowed.'
        return v

    @validator('model', each_item=True)
    def check_model_not_empty(cls, v):
        assert v != '', 'Empty strings are not allowed.'
        return v

class VehicleDataReader:
    ID = "key"
    VIN = "vin"
    YEAR = "year"
    MAKE = "make"
    MODEL = "model"
    TRIM = "trim"
    MILEAGE = "mileage"
    ZIP = "zip"
    OPTIONS = "options"
    ERRORS = "errors"
    VALIDATION = "validation"

    CSV_ID_COLUMN = "ID"
    CSV_VIN_COLUMN = "VIN"
    CSV_YEAR_COLUMN = "Year"
    CSV_MAKE_COLUMN = "MakeName"
    CSV_MODEL_COLUMN = "ModelName"
    CSV_TRIM_COLUMN = "BodyStyle"
    CSV_OPTION_COLUMN = "OptionsDescription"
    CSV_MILEAGE_COLUMN = "Mileage"


    def __init__(self, validation=None, limit=float("inf")) -> None:
        self.vehicleData = {}
        self.validation = validation
        self.limit = limit

    def csvInput(self, csvData):
        csvReader = csv.DictReader(io.StringIO(csvData))
        count = 0
        for row in csvReader:
            if float(count) == self.limit:
                break
            id = row.get(self.CSV_ID_COLUMN, count+1)
            vin = row.get(self.CSV_VIN_COLUMN, None)
            year = row.get(self.CSV_YEAR_COLUMN, None)
            make = row.get(self.CSV_MAKE_COLUMN, None)
            model = row.get(self.CSV_MODEL_COLUMN, None)
            trim = row.get(self.CSV_TRIM_COLUMN, "")
            mileage = row.get(self.CSV_MILEAGE_COLUMN, None)
            

            if mileage:
                mileage = mileage.replace('"', "").replace(",", "")
                if mileage.isdigit():
                    mileage = int(mileage)
                else:
                    mileage = None

            option = row.get(self.CSV_OPTION_COLUMN, [])
            
            key = vin if vin else str(id)

            if key not in self.vehicleData:
                options = list()
                if option:
                    options.append(option)
                try:
                    vehicle = Vehicle(**{self.ID: key,
                           self.VIN: vin, 
                           self.YEAR: year, 
                           self.MAKE: make, 
                           self.MODEL: model, 
                           self.TRIM: model + ' ' + trim, 
                           self.MILEAGE: mileage, 
                           self.OPTIONS: options,
                           self.VALIDATION: self.validation
                           }).__dict__
                except Exception as e:
                    vehicle = {self.ID: id,
                           self.VIN: vin, 
                           self.YEAR: year, 
                           self.MAKE: make, 
                           self.MODEL: model, 
                           self.TRIM: model + ' ' + trim, 
                           self.MILEAGE: mileage, 
                           self.OPTIONS: options,
                           self.VALIDATION: self.validation,
                           self.ERRORS: str(e)
                           }
                self.vehicleData[key] = vehicle
                count += 1
            else:
                if option:
                    if isinstance(self.vehicleData[key], Vehicle):
                        options = getattr(self.vehicleData[key], self.OPTIONS)
                        options = list(set(options.append(option)))
                        setattr(self.vehicleData[key], self.OPTIONS, options)
                    else:
                        self.vehicleData[key][self.OPTIONS].append(option)

        return self.vehicleData

    def jsonInput(self, jsonData):
        count = 0
        for row in jsonData.get("vehicles", None):
            if float(count) == self.limit:
                break
            count += 1
            id = row.get(self.ID, count+1)
            vin = row.get(self.VIN)
            key = vin if vin else str(id)
            row[self.ID] = key
            row[self.VALIDATION] = self.validation
            try:
                self.vehicleData[key] = Vehicle(**row).__dict__
            except Exception as e:
                row[self.ERRORS] = str(e)
                self.vehicleData[key] = row
        return self.vehicleData



