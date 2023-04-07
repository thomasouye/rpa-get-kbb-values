import requests
from datetime import datetime, timedelta
from time import sleep
import re

class Kbb:
    #KBB Settings
    KBB_API_ENDPOINT = "https://sandbox.api.kbb.com/idws/"
    KBB_VIN_ENDPOINT = "vehicle/vin/id/"
    KBB_VEHICLE_VALUE_ENDPOINT = "vehicle/values"
    KBB_VEHICLE_MAKE_ENDPOINT = "vehicle/makes"
    KBB_VEHICLE_LIMIT = 500
    KBB_VEHICLE_MODEL_ENDPOINT = "vehicle/models"
    KBB_VEHICLE_VEHICLES_ENDPOINT = "vehicle/vehicles"
    KBB_SUCCESS_LOG_MESSAGE = "KBB API call made!"
    KBB_TIME_WAIT = 1 #Seconds to wait between calls
    DEFAULT_ZIP = "96819"
    TRIM_CONVERSION = {
        "PKUP": "Pickup",
        "PR": "Premium",
        "P": "Premium",
        "SPT": "Sport",
        "LT": "Limited",
        "LMT": "Limited",
        "OFF": "Off-Road",
        "A-6'": "6 ft",
        "D-5'": "5 ft",
        "2WD": "2WD",
        "4x2": "2WD",
        "4WD": "4WD",
        "4x4": "4WD",
        "L4": "4-Cyl",
        "LV8": "V8"
    }

    OPTION_CONVERSION={
        "Package": "Pkg",
        "Moonroof": "Moon roof",
        "Wheel": "Wheels"
    }

    OPTION_IGNORE = ["Fixed"]

    OPTIONS_IN_TRIM = [
        "4WD",
        "2WD",
        "V6",
        "4-Cyl",
        "V8",
        "Hybrid"
    ]
    #Number of words in an option that need to match the KBB side
    OPTION_MATCH_WORD_COUNT = 2 
    #Percentage of words that need to match
    OPTION_MATCH_PERCENTAGE=0.51
    #If any of these words are in the option, match the KBB side and bypass the word count
    BYPASS_OPTIONS = [
        "Sonar",
        "Entune"
    ]

    def __init__(self, api_key) -> None:
        self.api_key = api_key
        self.resetRequest()
        self.vehicle = {}
        self.lastRequestTime = datetime.now() - timedelta(seconds=1)
        self.trims = {}
        self.values = {}
        self.servcoTrimName = ""
        self.optionCodes = set()
        self.optionCodeNames = set()
        self.originalOptionNames = set()
        self.usedLowestPricedTrim = False
        self.callsMade = 0
        self.rateLimit = 0

    def resetRequest(self):
        self.url = ""
        self.params = {"api_key": self.api_key}
        self.data = {}
        self.requestType = ""
        self.lastRequestTime = datetime.now()

    def doneProcessingVehicle(self):
        self.resetRequest()
        self.vehicle = {}
        self.trims = {}
        self.values = {}
        self.servcoTrimName = ""
        self.optionCodes = set()
        self.optionCodeNames = set()
        self.originalOptionNames = set()
        self.usedLowestPricedTrim = False
        self.callsMade = 0

    def setParams(self, params):
        self.params.update(params)

    def submitRequest(self):
        while (datetime.now() - self.lastRequestTime).total_seconds() < self.KBB_TIME_WAIT:
            sleep(self.KBB_TIME_WAIT/5)
        if self.requestType == "POST":
            ret = requests.post(self.KBB_API_ENDPOINT + self.url, params = self.params, json = self.data)
        else: #DEFAULT IS GET
            ret = requests.get(self.KBB_API_ENDPOINT + self.url, params=self.params)
        if ret.status_code == 200:
            self.callsMade += 1
            print(self.KBB_SUCCESS_LOG_MESSAGE)
        self.resetRequest()
        if "X-RateLimit-Remaining-Day" in ret.headers:
            self.rateLimit = ret.headers["X-RateLimit-Remaining-Day"]
        try:
            return ret.json()
        except:
            raise Exception('The KBB API responded with a ' + str(ret.status_code) + ' status code: ' + ret.content.decode("utf-8"))

    def getTrimsByVin(self, vin):
        self.params["VehicleClass"] = "UsedCar"
        self.url = self.KBB_VIN_ENDPOINT + vin
        result =  self.submitRequest()
        if "vinResults" in result:
            self.trims = result["vinResults"]
            return self.trims
        else: 
            raise Exception(result["message"])

    def replace(self,match):
        return self.TRIM_CONVERSION[match.group(0)]

    def convertServcoTrimName(self, trimName):
        #return re.sub('|'.join(r'\b%s\b' % re.escape(s) for s in self.TRIM_CONVERSION), self.replace, trimName) 
        convertedTrimName = ''
        for trimWord in trimName.split():
            for acro, word in self.TRIM_CONVERSION.items():
                if acro == trimWord:
                    trimWord = word
                    break
            convertedTrimName += trimWord + ' '
        return convertedTrimName.strip()
        # for acro, word in self.TRIM_CONVERSION.items():
        #     for trimWord in trimName.split():
        #         convertedTrimName += trimWord.replace(acro, word)
        # return trimName

    def convertServcoOptionName(self, optionName):
        convertedOptionName = ''
        for optionWord in optionName.replace("&", " ").split():
            for word, replacement in self.OPTION_CONVERSION.items():
                if word.upper() == optionWord.upper():
                    optionWord = replacement
                    break
            convertedOptionName += optionWord + ' '
        return convertedOptionName.strip()

    def getTrimNames(self):
        trimNames = []
        for trim in self.trims:
            trimNames.append(trim["trimName"])
        return trimNames

    def getVehicleByVinAndTrim(self, vin, trimName):
        self.trims = self.getTrimsByVin(vin)
        trims = self.trims
        trimWords = trimName.split()
        for trimWord in trimWords:
            if len(trims) == 1:
                break
            saveTrims = trims
            trims = list(filter(lambda x: (trimWord in x["trimName"].split()), trims))
            trimNames = []
            for trim in trims:
                trimNames.append(trim["trimName"])

            if len(trims) == 0:
                trims = saveTrims
        if len(trims) == 1:
            self.vehicle = trims[0]
            return trims[0] 
        else:
            return None

    def getVehicleByLowestPricedTrim(self, mileage, zipCode):
        useValue = float("inf")
        useTrim = {}
        currValue = float("inf")
        #Try to find the lowest priced trim
        for trim in self.trims:
            trimValues = self.getValueByVehicleId(trim["vehicleId"], mileage, zipCode, [])["prices"]
            for value in trimValues:
                #Use 'Typical Listing Price' 
                if value["priceTypeId"] == 2:
                    currValue = value["configuredValue"]
                    break
            if useValue > currValue:
                useValue = currValue
                useTrim = trim 
        self.usedLowestPricedTrim = True
        self.vehicle = useTrim
        return useTrim

    def getVehicleIdByVinAndTrim(self, vin, trimName):
        return self.getVehicleByVinAndTrim(vin, trimName)

    def getValueByVehicleId(self, vehicleId, mileage, zipCode, vehicleOptionIds):
        self.data = {"configuration": {"vehicleId": vehicleId, "vehicleOptionIds": list(vehicleOptionIds)}, "mileage": mileage, "zipCode": zipCode}
        self.url = self.KBB_VEHICLE_VALUE_ENDPOINT
        self.requestType = "POST"
        self.values = self.submitRequest()
        return self.values

    def getOptionNamesFromTrimName(self, options):
        for trimWord in self.servcoTrimName.split():
            if trimWord in self.OPTIONS_IN_TRIM:
                options.add(trimWord)
        return options

    def convertOptionNames(self, options):
        convertedOptions = list(map(self.convertServcoOptionName, options))
        return convertedOptions

    def getVehicleOptionCodes(self, options):
        KBBVehicleOptions = self.vehicle["vehicleOptions"]
        
        options = self.getOptionNamesFromTrimName(options)

        self.originalOptionNames = options
        options = self.convertOptionNames(options)
        optionCodes = set()
        optionCodeNames = set()
        for option in options:
            matchCount = 0

            #Ignore options that are blacklisted in self.OPTION_IGNORE
            blacklisted = False
            for blacklist in self.OPTION_IGNORE:
                if blacklist in option.split():
                    blacklisted = True
                    break
            if blacklisted:
                break
            
            for optionWord in option.split():
                savedOptions = KBBVehicleOptions
                KBBVehicleOptions = list(filter(lambda x: (optionWord.upper() in x["optionName"].replace(",", "").upper().split()), KBBVehicleOptions))
                
                if len(KBBVehicleOptions) == 1:  #Only one option remains
                    matchCount += 1
                    if optionWord in self.BYPASS_OPTIONS or optionWord in self.OPTIONS_IN_TRIM or (matchCount == self.OPTION_MATCH_WORD_COUNT and (matchCount/len(KBBVehicleOptions[0]["optionName"].split()) > self.OPTION_MATCH_PERCENTAGE)):
                        optionCodes.add(KBBVehicleOptions[0]["vehicleOptionId"])
                        optionCodeNames.add(str(KBBVehicleOptions[0]["vehicleOptionId"]) + " - " + KBBVehicleOptions[0]["optionName"])
                        break
                elif len(KBBVehicleOptions) > 0: #At least one option matched the current word
                    matchCount+=1
                elif len(KBBVehicleOptions) == 0:  #None of the options matched the current word so reset
                    KBBVehicleOptions = savedOptions
            KBBVehicleOptions = self.vehicle["vehicleOptions"]
        self.optionCodes = optionCodes
        self.optionCodeNames = optionCodeNames
        return optionCodes


    def getValueByVinAndTrim(self, vin, trimName, mileage, zipCode, options):
        vehicle = self.getVehicleIdByVinAndTrim(vin, trimName)
        if not vehicle:
            vehicle = self.getVehicleByLowestPricedTrim(mileage, zipCode)
        
        vehicleId = vehicle["vehicleId"]

        vehicleOptionIds = self.getVehicleOptionCodes(options)
        # for index in vehicle["vinResults"][0]["vehicleOptions"]:
        #     vehicleOptionIds.push(vehicle["vinResults"][0]["vehicleOptions"][index]["vehicleOptionId"])
        value = self.getValueByVehicleId(vehicleId, mileage, zipCode, vehicleOptionIds)
        return value

    def getMakeIdByName(self, makeName):
        self.params["limit"] = self.KBB_VEHICLE_LIMIT
        self.url = self.KBB_VEHICLE_MAKE_ENDPOINT
        makes = self.submitRequest()
        makeId = 0
        for make in makes["items"]:
            if make["makeName"].upper() == makeName.upper():
                makeId = make["makeId"]
                exit
        if not makeId > 0:
            raise Exception("Could not determine KBB make ID")
        return makeId

    def getModelIdByName(self, year, makeId, modelName):
        self.params["limit"] = self.KBB_VEHICLE_LIMIT
        self.params["makeid"] = makeId
        self.params["yearid"] = year
        self.url = self.KBB_VEHICLE_MODEL_ENDPOINT
        models = self.submitRequest()
        modelIds = []
        for model in models["items"]:
            #Only doing a direct compare for now, possible regex compare later
            if model["modelName"].upper() == modelName.upper(): 
                modelIds.append(model["modelId"])
                exit
        if len(modelIds) == 0:
            raise Exception("Could not determine KBB model ID")
        elif len(modelIds) > 1: #technically not necessary for now
            raise Exception("Could not narrow down KBB model IDs: " + str(modelIds))
        return modelIds[0]

    def getVehicleByName(self, year, makeName, modelName, trimName):
        makeId = self.getMakeIdByName(makeName)
        modelId = self.getModelIdByName(year, makeId, modelName)
        self.params["limit"] = self.KBB_VEHICLE_LIMIT
        self.params["modelId"] = modelId
        self.params["yearId"] = year
        self.url = self.KBB_VEHICLE_VEHICLES_ENDPOINT
        trims = self.submitRequest()
        vehicles = trims["items"]
        trimWords = trimName.split()

        for trimWord in trimWords:
            vehicles = list(filter(lambda x: (trimWord in x["trimName"].split()), vehicles))
            if len(vehicles) == 1:
                exit
        if len(vehicles) != 1:
            raise Exception("Could not narrow down KBB trims: " + str(vehicles))
        return vehicles[0]

    def getVehicleIdByName(self, year, makeName, modelName, trimName):
        vehicle = self.getVehicleByName(year, makeName, modelName, trimName)
        return vehicle["vehicleId"]
    

    def getValueByName(self, year, makeName, modelName, trimName, mileage, zipCode, vehicleOptionIds = None):
        vehicleId = self.getVehicleIdByName(year, makeName, modelName, trimName)
        return self.getValueByVehicleId(vehicleId, mileage, zipCode, vehicleOptionIds)

    def compareVehicleVinAndName(self, vin, year, makeName, modelName, trimName):
        return self.getVehicleIdByName(year, makeName, modelName, trimName) == self.getVehicleIdByVinAndTrim(vin, trimName)

    def getVehicleValueReportByVINAndTrim(self, vin, trimName, mileage, zipCode, vehicleOptions):
        errors = []
        configuredValue = 0
        matchedVehicle = ""
        vehicleId = 0
        trimNameConverted = trimName
        trimNameConverted = self.convertServcoTrimName(trimName)
        self.servcoTrimName = trimNameConverted
        values = {}
        try:
            values = self.getValueByVinAndTrim(vin, trimNameConverted, mileage, zipCode, vehicleOptions)
            vehicleId = self.vehicle["vehicleId"]
            configuredValue = values["prices"][0]["configuredValue"]
            matchedVehicle = self.vehicle["trimName"]
        except Exception as e:
            errors.append(str(e))
        trimNames = self.getTrimNames()
        optionCodeNames = self.optionCodeNames
        originalOptionNames = self.originalOptionNames
        availableVehicleOptions = []
        if "vehicleOptions" in self.vehicle:
            availableVehicleOptions = self.vehicle["vehicleOptions"]
        usedLowestPricedTrim = self.usedLowestPricedTrim
        callsMade = self.callsMade
        self.doneProcessingVehicle()
        return {"errors": errors,
                "numCallsMade": callsMade, 
                "vin": vin, 
                "usedLowestPricedTrim": usedLowestPricedTrim,
                "matchedVehicle": matchedVehicle, 
                "matchedOptions": list(optionCodeNames), 
                "configuredValue": configuredValue, 
                "originalTrim": trimName, 
                "convertedTrim": trimNameConverted, 
                "availableTrims": trimNames, 
                "vehicleId": vehicleId, 
                "originalOptions": list(originalOptionNames), 
                "availableOptions": str( [x["optionName"] for x in availableVehicleOptions ]),
                "prices": values["prices"]
                }