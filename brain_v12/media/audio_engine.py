"""Native procedural audio primitives for BRAIN films.
Creates a deterministic WAV bed without external media-generation services."""
from __future__ import annotations
import math,wave,struct
def tone(path:str,duration:float,freq:float=220.0,rate:int=48000):
    n=max(1,int(duration*rate))
    with wave.open(path,"wb") as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate)
        for i in range(n):
            t=i/rate
            env=min(1,t*12,(duration-t)*12,1)
            sample=int(12000*env*math.sin(2*math.pi*freq*t))
            w.writeframes(struct.pack("<h",sample))
    return path
