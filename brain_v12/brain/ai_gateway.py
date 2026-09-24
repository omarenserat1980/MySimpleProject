class AIGateway:
    def __init__(self): self.providers={}
    def register(self,name,modalities,handler=None): self.providers[name]={"name":name,"modalities":modalities,"enabled":handler is not None,"handler":handler}; return self.providers[name]
    def status(self): return [{"name":k,"modalities":v["modalities"],"enabled":v["enabled"]} for k,v in self.providers.items()]
    def enabled_providers(self, modality=None):
        items=[]
        for name,item in self.providers.items():
            if item["enabled"] and (modality is None or modality in item["modalities"]):
                items.append(name)
        return items

    def invoke(self,provider,modality,payload):
        item=self.providers.get(provider)
        if not item: return {"ok":False,"error":"PROVIDER_NOT_REGISTERED"}
        if modality not in item["modalities"]: return {"ok":False,"error":"MODALITY_NOT_SUPPORTED"}
        if not item["handler"]: return {"ok":False,"error":"PROVIDER_NOT_CONFIGURED"}
        return {"ok":True,"result":item["handler"](payload)}
