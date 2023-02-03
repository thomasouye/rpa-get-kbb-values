import requests

class Kbb:
    #KBB Settings
    KBB_API_ENDPOINT = "https://sandbox.api.kbb.com/idws/"
    KBB_VIN_ENDPOINT = "vehicle/vin/id/"
    KBB_VEHICLE_VALUE_ENDPOINT = "vehicle/values"

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
            ret = requests.post(self.KBB_API_ENDPOINT + self.url, params = self.params, data = self.data)
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




