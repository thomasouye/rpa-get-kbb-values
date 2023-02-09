import requests

class Kbb:
    #KBB Settings
    KBB_API_ENDPOINT = "https://sandbox.api.kbb.com/idws/"
    KBB_VIN_ENDPOINT = "vehicle/vin/id/"
    KBB_VEHICLE_VALUE_ENDPOINT = "vehicle/values"
    KBB_VEHICLE_MAKE_ENDPOINT = "vehicle/makes"
    KBB_VEHICLE_LIMIT = 500
    KBB_VEHICLE_MODEL_ENDPOINT = "vehicle/models"
    KBB_VEHICLE_VEHICLES_ENDPOINT = "vehicle/vehicles"

    def __init__(self, api_key) -> None:
        self.api_key = api_key
        self.resetVariables()

    def resetVariables(self):
        self.url = ""
        self.params = {"api_key": self.api_key}
        self.data = {}
        self.requestType = ""

    def setParams(self, params):
        self.params.update(params)

    def submitRequest(self):
        if self.requestType == "POST":
            ret = requests.post(self.KBB_API_ENDPOINT + self.url, params = self.params, json = self.data)
        else: #DEFAULT IS GET
            ret = requests.get(self.KBB_API_ENDPOINT + self.url, params=self.params)
        self.resetVariables()
        try:
            return ret.json()
        except:
            raise Exception('The KBB API responded with a ' + str(ret.status_code) + ' status code: ' + ret.content.decode("utf-8"))

    def getVehicleByVin(self, vin):
        self.params["VehicleClass"] = "UsedCar"
        self.url = self.KBB_VIN_ENDPOINT + vin
        vehicle = self.submitRequest()
        return vehicle

    def getVehicleIdByVin(self, vin):
        vehicle = self.getVehicleByVin(vin)
        return vehicle["vinResults"][0]["vehicleId"]

    def getValueByVehicleId(self, vehicleId, mileage, zipCode, vehicleOptionIds):
        self.data = {"configuration": {"vehicleId": vehicleId, "vehicleOptionIds": vehicleOptionIds}, "mileage": mileage, "zipCode": zipCode}
        self.url = self.KBB_VEHICLE_VALUE_ENDPOINT
        self.requestType = "POST"
        value = self.submitRequest()
        return value

    def getValueByVin(self, vin, mileage, zipCode):
        vehicle = self.getVehicleByVin(vin)
        vehicleId = vehicle["vinResults"][0]["vehicleId"]
        vehicleOptionIds = []
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
        print(vehicles[0]["vehicleId"])
        return vehicles[0]

    def getVehicleIdByName(self, year, makeName, modelName, trimName):
        vehicle = self.getVehicleByName(year, makeName, modelName, trimName)
        return vehicle["vehicleId"]
    

    def getValueByName(self, year, makeName, modelName, trimName, mileage, zipCode, vehicleOptionIds = None):
        vehicleId = self.getVehicleIdByName(year, makeName, modelName, trimName)
        return self.getValueByVehicleId(vehicleId, mileage, zipCode, vehicleOptionIds)

    def compareVehicleVinAndName(self, vin, year, makeName, modelName, trimName):
        return self.getVehicleIdByName(year, makeName, modelName, trimName) == self.getVehicleIdByVin(vin)