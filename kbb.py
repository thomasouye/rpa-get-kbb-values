import requests
from datetime import datetime, timedelta
from time import sleep

class Kbb:
    #KBB Settings
    KBB_API_ENDPOINT = "https://api.kbb.com/idws/"
    KBB_VIN_ENDPOINT = "vehicle/vin/id/"
    KBB_VEHICLE_VALUE_ENDPOINT = "vehicle/values"
    KBB_VEHICLE_MAKE_ENDPOINT = "vehicle/makes"
    KBB_OPTION_ENDPOINT = "vehicle/vehicleoptions"
    KBB_VEHICLE_MODEL_ENDPOINT = "vehicle/models"
    KBB_VEHICLE_VEHICLES_ENDPOINT = "vehicle/vehicles"
    KBB_VEHICLE_CONFIG_ENDPOINT = "vehicle/applyconfiguration"
    KBB_VEHICLE_LIMIT = 500 #500 is the max limit to send to KBB
    KBB_SUCCESS_LOG_MESSAGE = "KBB API call made!"
    KBB_TIME_WAIT = 0 #Seconds to wait between calls
    KBB_RETRY_WAIT = 1 #Seconds to wait before retrying a call
    KBB_MAX_RETRIES = 60 #Number of retries before failing a vehicle pricing
    DEFAULT_ZIP = "96819" #Default zip code for kbb pricing

    #Convert Servco trim names -> KBB trim names
    TRIM_CONVERSION = {
        "PKUP": "Pickup",
        "PR": "Premium",
        "P": "Premium",
        "PREM": "Premium",
        "SPT": "Sport",
        "LT": "Limited",
        "LTD": "Limited",
        "LMT": "Limited",
        "TOUR": "Touring",
        "OFF": "Off-Road",
        "A-6'": "6 ft",
        "D-5'": "5 ft",
        "2WD": "2WD",
        "4x2": "2WD",
        "4WD": "4WD",
        "4x4": "4WD",
        "L4": "4-Cyl",
        "LV8": "V8",
        "WAG": "Wagon",
        "SDN": "Sedan",
        "6MT": "Manual 6-Spd",
        "5MT": "Manual 5-Spd"
    }

    #Ignore the trim word if it is one of these (ALL CAPS)
    TRIM_IGNORE = ["EDITION"]

    #Remove substrings in this list from options
    OPTION_REMOVE =[
        "w/",
        ",",
        "(",
        ")"
    ]

    #Convert Servco option names -> Kbb names
    OPTION_CONVERSION={
        "&": " ",
        "Package": "Pkg",
        "Power Moonroof": "Moon Roof",
        "Moonroof": "Moon Roof",
        "Wheel": "Wheels",
        "Blind Spot": "Blind-Spot",
        "Navi": "Navigation",
        "Off Road": "Off-Road"
    }

    #Ignore the option if it has any of the words in OPTION_IGNORE
    OPTION_IGNORE = ["Fixed", "Wheel Locks", "Delete"]

    #Options that are included in the Servco trim name
    OPTIONS_IN_TRIM = [
        "4WD",
        "2WD",
        "V6",
        "4-Cyl",
        "V8",
        "Hybrid",
        "AWD",
        "CVT",
        "Manual",
        "I-FORCE"
    ]
    #Number of words in an option that need to match the KBB side ***Out of use currently, went with percentage instead
    OPTION_MATCH_WORD_COUNT = 2 

    #Percentage of words that need to match as a decimal
    OPTION_MATCH_PERCENTAGE=0.51

    #If any of these words are in the option, match the KBB side and bypass the word count/percentage
    BYPASS_OPTIONS = [
        "Sonar",
        "Entune",
        "ABS",
        "FWD",
        "Blind-Spot",
        "Starlink"
    ]

    def __init__(self, api_key, report = False) -> None:
        self.api_key = api_key
        self.resetRequest()
        self.id = 0
        self.vehicle = {}
        #self.valuationDate = ""
        self.lastRequestTime = datetime.now() - timedelta(seconds=1)
        self.trims = {}
        self.values = {}
        self.servcoTrimName = ""
        self.servcoModelName = ""
        self.originalOptionNames = []
        self.typicalOptions = []
        self.vinDecodedOptions = []
        self.matchedOptions = []
        self.configuration = []
        self.configurationWithNames = []
        self.usedLowestPricedTrim = False
        self.callsMade = 0
        self.rateLimit = float("inf")
        self.report = report
        self.debug = False
        self.warnings = []
    
    def print(self, string):
        if self.debug:
            print(string)

    def resetRequest(self):
        self.url = ""
        self.params = {"api_key": self.api_key}
        self.data = {}
        self.requestType = ""
        self.lastRequestTime = datetime.now()

    def doneProcessingVehicle(self):
        self.resetRequest()
        self.id = 0
        #self.valuationDate = ""
        self.vehicle = {}
        self.trims = {}
        self.values = {}
        self.servcoTrimName = ""
        self.originalOptionNames = []
        self.typicalOptions = []
        self.vinDecodedOptions = []
        self.matchedOptions = []
        self.configuration = []
        self.configurationWithNames = []
        self.usedLowestPricedTrim = False
        self.callsMade = 0
        self.warnings = []

    def setParams(self, params):
        self.params.update(params)

    def submitRequest(self, retries=99): #20 max retries before failing a request ~20 seconds per request
        #print('----BEGIN KBB CALL--------')
        if retries > self.KBB_MAX_RETRIES:
            retries = self.KBB_MAX_RETRIES
        while (datetime.now() - self.lastRequestTime).total_seconds() < self.KBB_TIME_WAIT:
            sleep(self.KBB_TIME_WAIT/5)
        if self.requestType == "POST":
            #print("------REQUEST DATA:" + str(self.data))
            #print("------REQUEST PARAMS: " + str(self.params))
            ret = requests.post(self.KBB_API_ENDPOINT + self.url, params = self.params, json = self.data)
        else: #DEFAULT IS GET
            #print("------VIN LOOKUP: " + self.url)
            #print("------REQUEST PARAMS: " + str(self.params))
            ret = requests.get(self.KBB_API_ENDPOINT + self.url, params=self.params)
        if "X-RateLimit-Remaining-Day" in ret.headers: 
            self.rateLimit = float(ret.headers["X-RateLimit-Remaining-Day"]) #Update the remaining daily count
        if ret.status_code == 429: #Retry if hit the per second rate limit
            if "X-RateLimit-Remaining-Day" in ret.headers and float(ret.headers["X-RateLimit-Remaining-Day"]) > 0:
                sleep(self.KBB_RETRY_WAIT)
                #print("Retry #: " + str(self.KBB_MAX_RETRIES + 1 - retries) + " out of " + str(self.KBB_MAX_RETRIES))
                return self.submitRequest(retries-1)
        jsonResponse = ret.json()
        #print("------KBB RESPONSE: " + str(jsonResponse))
        #print("----END KBB CALL-------")
        if "warnings" in jsonResponse:
            self.warnings = self.warnings + ret.json()["warnings"]
        self.resetRequest()
        if ret.status_code == 200:
            self.callsMade += 1
            #print(self.KBB_SUCCESS_LOG_MESSAGE)
            return jsonResponse
        raise Exception('The KBB API responded with a ' + str(ret.status_code) + ' status code: ' + ret.content.decode("utf-8"))

    def getTrimsByVin(self, vin):
        self.params["VehicleClass"] = "UsedCar"
        self.url = self.KBB_VIN_ENDPOINT + vin
        result =  self.submitRequest()
        if "vinResults" in result:
            self.trims = result["vinResults"]
            return self.trims
        else: 
            if "message" in result:
                raise Exception(result["message"])
            else:
                raise Exception(str(result))

    def convertServcoTrimName(self, trimName):
        convertedTrimName = []
        for trimWord in trimName.split():
            if trimWord.upper() in self.TRIM_IGNORE:
                break
            for acro, word in self.TRIM_CONVERSION.items():
                if acro.upper() == trimWord.upper():
                    trimWord = word
                    break
            convertedTrimName.append(trimWord)
        #print(' '.join(convertedTrimName))
        return ' '.join(convertedTrimName)
        # for acro, word in self.TRIM_CONVERSION.items():
        #     for trimWord in trimName.split():
        #         convertedTrimName += trimWord.replace(acro, word)
        # return trimName

    def convertServcoOptionName(self, optionName):
        convertedOptionName = []
        match = False
        for word in optionName.split():
            for replace, replacement in self.OPTION_CONVERSION.items():
                if replace.upper() == word.upper():
                    convertedOptionName.append(replacement.upper())
                    match = True
                    break
            if not match:
                convertedOptionName.append(word)
        return " ".join(convertedOptionName)

    def filterServcoOptions(self, options):
        for blacklist in self.OPTION_IGNORE:
            options = [option for option in options if not blacklist.upper() in option.upper()]
        return options

    def getTrimNames(self):
        trimNames = []
        if self.trims:
            for trim in self.trims:
                trimNames.append(trim["trimName"])
        return trimNames

    def getVehicleByVinAndTrim(self, vin, trimName):
        self.trims = self.getTrimsByVin(vin)
        trims = self.trims
        trimWords = []
        if trimName:
            trimWords = trimName.split()
        for trimWord in trimWords:
            if len(trims) == 1:
                break
            saveTrims = trims
            trims = list(filter(lambda x: (trimWord.upper() in (y.upper() for y in x["trimName"].split())), trims))
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
        trimValues = []
        #Try to find the lowest priced trim
        for trim in self.trims:
            values = self.getValueByVehicleId(trim["vehicleId"], mileage, zipCode, [])
            if "prices" in values:
                trimValues = values["prices"]
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
        self.data = {"configuration": {"vehicleId": vehicleId, "vehicleOptionIds": list(vehicleOptionIds)}, "mileage": mileage, "zipCode": zipCode}#, "valuationDate": self.valuationDate}
        self.url = self.KBB_VEHICLE_VALUE_ENDPOINT
        self.requestType = "POST"
        self.values = self.submitRequest()
        #print(self.values)
        return self.values

    def getOptionsByVehicleId(self, vehicleId):
        self.params["limit"] = self.KBB_VEHICLE_LIMIT
        self.params["vehicleId"] = vehicleId
        self.url = self.KBB_OPTION_ENDPOINT
        self.requestType = "GET"
        options = self.submitRequest()
        self.vehicle["vehicleOptions"] = options.get("items")
        return self.values

    def getTypicalOptions(self):
        for option in self.vehicle["vehicleOptions"]:
            if option["isTypical"]:
                self.typicalOptions.append(option)
                self.configuration.append(option["vehicleOptionId"])
            if "isVinDecoded" in option and option["isVinDecoded"]:
                self.vinDecodedOptions.append(option)

    def updateConfiguration(self, newConfigurationIds):
        self.data = {}
        self.data["StartingConfiguration"] = {"VehicleId": self.vehicle["vehicleId"]}
        if self.configuration:
            self.data["StartingConfiguration"]["vehicleOptionIds"] = self.configuration

        self.data["ConfigurationChanges"] = []
        sequence = 1
        for configuration in newConfigurationIds:
            self.data["ConfigurationChanges"].append({"Sequence": sequence, "VehicleOptionId": configuration, "Action": "selected"})

        self.url = self.KBB_VEHICLE_CONFIG_ENDPOINT
        self.requestType = "POST"
        response = self.submitRequest()

        if "finalConfiguration" in response and "vehicleOptionIds" in response["finalConfiguration"]:
            self.configuration = response["finalConfiguration"]["vehicleOptionIds"]

    def getConfiguration(self):
        self.getTypicalOptions()

        vehicleConfiguration = []
        for option in self.matchedOptions:
            vehicleConfiguration.append(option["vehicleOptionId"])
        for option in self.vinDecodedOptions:
            vehicleConfiguration.append(option["vehicleOptionId"])

        self.updateConfiguration(vehicleConfiguration)

    def getOptionNamesFromTrimName(self, options):
        if self.servcoTrimName:
            for trimWord in self.servcoTrimName.split():
                if trimWord.upper() in (x.upper() for x in self.OPTIONS_IN_TRIM):
                    options.append(trimWord)
        return options

    def getOptionNamesFromModelName(self, options):
        if self.servcoModelName:
            for trimWord in self.servcoModelName.split():
                if trimWord.upper() in (x.upper() for x in self.OPTIONS_IN_TRIM):
                    options.append(trimWord)
        return options

    def convertOptionNames(self, options):
        convertedOptions = self.filterServcoOptions(options)
        convertedOptions = self.cleanOptionNames(convertedOptions) ## clean the options here too
        convertedOptions = list(map(self.convertServcoOptionName, convertedOptions))
        return convertedOptions

    def cleanKBBOptionNames(self, options):
        for index in range(len(options)):
            for substr in self.OPTION_REMOVE:
                options[index]['optionName'] = options[index]['optionName'].replace(substr, "")
        return options

    def cleanOptionNames(self, options):
        for index in range(len(options)):
            for substr in self.OPTION_REMOVE:
                options[index] = options[index].replace(substr, "")
        return options

    def getMatchingVehicleOptionCodes(self, options):
        cleanedOptions = self.cleanKBBOptionNames(self.vehicle["vehicleOptions"])
        KBBVehicleOptions = cleanedOptions
        
        options = self.getOptionNamesFromTrimName(options)
        options = self.getOptionNamesFromModelName(options)
        if options:
            self.originalOptionNames = options
            options = self.convertOptionNames(options)
        matchedOptions = []
        #print(str(len(options)))
        for option in options:
            matchCount = 0
            #print('--------------------------------------------------------------')
            #print(option)
            for optionWord in option.split():
                savedOptions = KBBVehicleOptions
                KBBVehicleOptions = list(filter(lambda x: (optionWord.upper() in x["optionName"].replace(",", "").upper().split()), KBBVehicleOptions))
                #print('--' + optionWord)
                #print('--' + str( [x["optionName"] for x in KBBVehicleOptions ]))
                
                if len(KBBVehicleOptions) == 1:  #Only one option remains
                    matchCount += 1
                    #print('----' + str(matchCount))
                    if (optionWord.upper() in (x.upper() for x in self.BYPASS_OPTIONS)
                    or optionWord.upper() in (x.upper() for x in self.OPTIONS_IN_TRIM) 
                    or matchCount/len(KBBVehicleOptions[0]["optionName"].split()) > self.OPTION_MATCH_PERCENTAGE):
                        #print('*------' + str(KBBVehicleOptions[0]))
                        matchedOptions.append(KBBVehicleOptions[0])
                        break
                elif len(KBBVehicleOptions) > 0: #At least one option matched the current word
                    matchCount+=1
                elif len(KBBVehicleOptions) == 0:  #None of the options matched the current word so reset
                    KBBVehicleOptions = savedOptions
            KBBVehicleOptions = cleanedOptions
        #print(str(matchedOptions))
        self.matchedOptions = matchedOptions
        return matchedOptions

    def getValueByVinAndTrim(self, vin, trimName, mileage, zipCode, options):
        self.vehicle = self.getVehicleIdByVinAndTrim(vin, trimName)
        if not self.vehicle:
            self.vehicle = self.getVehicleByLowestPricedTrim(mileage, zipCode)
        vehicleId = self.vehicle["vehicleId"]
        self.getMatchingVehicleOptionCodes(options)
        self.getConfiguration()
        value = self.getValueByVehicleId(vehicleId, mileage, zipCode, self.configuration)
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
            raise Exception("Could not determine KBB make.")
        return makeId

    def getModelIdByName(self, year, makeName, modelName):
        makeId = self.getMakeIdByName(makeName)
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
            raise Exception("Could not determine KBB model.")
        elif len(modelIds) > 1: #technically not necessary for now
            raise Exception("Could not narrow down KBB model IDs: " + str(modelIds))
        return modelIds[0]

    def getTrimsByModelId(self, year, makeName, modelName):
        modelId = self.getModelIdByName(year, makeName, modelName)
        self.params["limit"] = self.KBB_VEHICLE_LIMIT
        self.params["modelId"] = modelId
        self.params["yearId"] = year
        self.url = self.KBB_VEHICLE_VEHICLES_ENDPOINT
        trims = self.submitRequest()
        return trims

    def getVehicleByName(self, year, makeName, modelName, trimName):
        trims = self.getTrimsByModelId(year, makeName, modelName)
        self.trims = trims["items"]
        vehicles = self.trims
        trimWords = trimName.split()
        for trimWord in trimWords:
            vehicles = list(filter(lambda x: (trimWord in x["trimName"].split()), vehicles))
            if len(vehicles) == 1:
                exit
        if len(vehicles) != 1:
            return None
        return vehicles[0]

    def getVehicleIdByName(self, year, makeName, modelName, trimName):
        vehicle = self.getVehicleByName(year, makeName, modelName, trimName)
        if vehicle and "vehicleId" in vehicle:
            self.vehicle = vehicle
            return vehicle["vehicleId"]
        else:
            return None

    def getVehicleIdByNameNoTrim(self, year, makeName, modelName, mileage, zipCode):
        self.trims = self.getTrimsByModelId(year, makeName, modelName)["items"]
        self.vehicle = self.getVehicleByLowestPricedTrim(mileage, zipCode)
        vehicleId = self.vehicle["vehicleId"]
        return vehicleId

    def getValueByName(self, year, makeName, modelName, trimName, mileage, zipCode, options = []):
        vehicleId = None
        if trimName and modelName.strip() != trimName.strip():
            vehicleId = self.getVehicleIdByName(year, makeName, modelName, trimName)
        if not vehicleId:
            vehicleId = self.getVehicleIdByNameNoTrim(year, makeName, modelName, mileage, zipCode)
        self.getOptionsByVehicleId(vehicleId)
        self.getMatchingVehicleOptionCodes(options)
        self.getConfiguration()
        return self.getValueByVehicleId(vehicleId, mileage, zipCode, self.configuration)

    def compareVehicleVinAndName(self, vin, year, makeName, modelName, trimName):
        return self.getVehicleIdByName(year, makeName, modelName, trimName) == self.getVehicleIdByVinAndTrim(vin, trimName)

    def addOptionNames(self):
        optionById = {}
        for option in self.vehicle.get("vehicleOptions"):
            optionById[str(option["vehicleOptionId"])] = option["optionName"]
        if "prices" in self.values:
            for i, price in enumerate(self.values.get("prices")):
                if "optionPrices" in price:
                    for j, option in enumerate(price.get("optionPrices")):
                        self.values["prices"][i]["optionPrices"][j]["optionName"] = optionById.get(option["vehicleOptionId"])
        if self.report:
            for optionId in self.configuration:
                self.configurationWithNames.append({"vehicleOptionId": optionId, "optionName": optionById.get(str(optionId))})



    def generateKBBReport(self, trimName, trimNameConverted, errors):
        warnings = self.warnings
        vehicleId = self.vehicle.get("vehicleId")
        configuredValue = None
        prices = {}
        if "prices" in self.values:
            configuredValue = self.values["prices"][0]["configuredValue"]
            self.addOptionNames()
            prices = self.values["prices"]
        #valuationDate = self.values.get("valuationDate")
        matchedVehicle = self.vehicle.get("modelName") + ' ' + self.vehicle.get("trimName")
        trimNames = self.getTrimNames()
        originalOptionNames = self.originalOptionNames
        matchedOptions = self.matchedOptions
        vinDecodedOptions = self.vinDecodedOptions
        typicalOptions = self.typicalOptions
        configuration = self.configurationWithNames
        availableVehicleOptions = ""
        if "vehicleOptions" in self.vehicle:
            availableVehicleOptions = str( [ x.get("optionName") + ' (' + str(x.get("vehicleOptionId")) + ')' for x in self.vehicle.get("vehicleOptions")])

        usedLowestPricedTrim = self.usedLowestPricedTrim
        callsMade = self.callsMade
        self.doneProcessingVehicle()
        return {"errors": errors,
                "warnings": [str(x) for x in warnings],
                "numCallsMade": callsMade, 
                #"valuationDate": valuationDate,
                "usedLowestPricedTrim": usedLowestPricedTrim,
                "originalTrim": trimName, 
                "convertedTrim": trimNameConverted, 
                "availableTrims": trimNames, 
                "matchedVehicle": matchedVehicle, 
                "matchedOptions": [str(x.get("optionName")) + " (" + str(x.get("vehicleOptionId")) + ")" for x in matchedOptions], 
                "vinDecodedOptions": [str(x.get("optionName")) + " (" + str(x.get("vehicleOptionId")) + ")" for x in vinDecodedOptions], 
                "typicalOptions": [str(x.get("optionName")) + " (" + str(x.get("vehicleOptionId")) + ")" for x in typicalOptions],
                "finalConfiguration": [str(x.get("optionName")) + " (" + str(x.get("vehicleOptionId")) + ")" for x in configuration],
                "originalOptions": list(originalOptionNames), 
                "availableOptions": availableVehicleOptions,
                "configuredValue": configuredValue, 
                "kbbVehicleId": vehicleId, 
                "prices": prices
                }

    def generateReturnValues(self, errors):
        callsMade = self.callsMade

        self.addOptionNames()
        prices = self.values.get("prices")
        usedLowestPricedTrim = self.usedLowestPricedTrim
        #valuationDate = self.values.get("valuationDate")
        warnings = self.warnings
        self.doneProcessingVehicle()
        return {"errors": errors,
                "warnings": [str(x) for x in warnings],
                #"valuationDate": valuationDate,
                "usedLowestPricedTrim": usedLowestPricedTrim,
                "numCallsMade": callsMade, 
                "prices": prices}

    def getVehicleValue(self, id, vin, year, makeName, modelName, trimName, mileage, zipCode, vehicleOptions): #valuationDate=datetime.today().strftime('%m/%d/%Y')):
        errors = []
        values = {}

        #self.valuationDate = valuationDate
        
        trimNameConverted = trimName
        if trimName:
            trimNameConverted = self.convertServcoTrimName(trimName)

        self.servcoTrimName = trimNameConverted

        modelNameConverted = modelName #this is only to grab options from model name
        if modelName:
            modelNameConverted = self.convertServcoTrimName(modelName)
        self.servcoModelName = modelNameConverted
        
        self.id = id
        try:
            if vin:
                values = self.getValueByVinAndTrim(vin, trimNameConverted, mileage, zipCode, vehicleOptions)
            else:
                values = self.getValueByName(year, makeName , modelName, trimNameConverted, mileage, zipCode, vehicleOptions)
            self.values = values
        except Exception as e:
            errors.append(str(e))
        if not self.originalOptionNames and vehicleOptions:
            self.originalOptionNames = vehicleOptions
        if self.report:
            return self.generateKBBReport(trimName, trimNameConverted, errors)
        else:
            return self.generateReturnValues(errors)