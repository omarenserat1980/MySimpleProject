class PluginManager:
    def __init__(self): self.plugins={}
    def register(self,plugin_id,name,version,capabilities=None,permissions=None):
        self.plugins[plugin_id]={"id":plugin_id,"name":name,"version":version,"capabilities":capabilities or [],"permissions":permissions or [],"status":"disabled","health":"unknown"}; return self.plugins[plugin_id]
    def enable(self,plugin_id):
        if plugin_id not in self.plugins: return {"ok":False,"error":"PLUGIN_NOT_FOUND"}
        self.plugins[plugin_id]["status"]="enabled"; self.plugins[plugin_id]["health"]="ready"; return self.plugins[plugin_id]
    def disable(self,plugin_id):
        if plugin_id not in self.plugins: return {"ok":False,"error":"PLUGIN_NOT_FOUND"}
        self.plugins[plugin_id]["status"]="disabled"; return self.plugins[plugin_id]
    def status(self): return list(self.plugins.values())
