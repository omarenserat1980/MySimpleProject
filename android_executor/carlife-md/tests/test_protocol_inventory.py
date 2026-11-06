#!/usr/bin/env python3
"""Static regression checks for the pinned CarLife MD protocol contract."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
HEADERS = ROOT / "upstream/LibSource/include"
wrapper = (HEADERS / "CCarLifeLibWrapper.h").read_text(errors="replace")
wire = (HEADERS / "CTranRecvPackageProcess.h").read_text(errors="replace")
connect = (HEADERS / "CConnectManager.h").read_text(errors="replace")

required_api = [
    "carLifeLibInit()", "connectionSetup(string mdIP, string interfaceName)",
    "cmdReceiveOperation()", "videoReceiveOperation()", "mediaReceiveOperation()",
    "ctrlReceiveOperation()", "cmdRegisterMdAuthenResponse", "cmdRegisterMdAuthenResult",
    "videoRegisterDataReceive", "mediaRegisterNormalData", "ctrlTouchActionDown",
]
for symbol in required_api:
    assert symbol in wrapper, f"Missing public API: {symbol}"

required_wire = [
    "CMD_CHANNEL=1", "VIDEO_CHANNEL=2", "MEDIA_CHANNEL=3", "TTS_CHANNEL=4",
    "VR_CHANNEL=5", "CTRL_CHANNEL=6", "MSG_CMD_HU_AUTHEN_REQUEST=0x00018048",
    "MSG_CMD_MD_AUTHEN_RESPONSE=0x00010049", "MSG_CMD_HU_AUTHEN_RESULT=0x0001804A",
    "MSG_CMD_MD_AUTHEN_RESULT=0x0001004B", "MSG_VIDEO_DATA = 0x00020001",
    "MSG_MEDIA_DATA = 0x00030006", "MSG_TOUCH_ACTION_DOWN = 0x00068002",
]
normalized_wire = re.sub(r"\s*=\s*", "=", wire)
for symbol in required_wire:
    normalized_symbol = re.sub(r"\s*=\s*", "=", symbol)
    assert normalized_symbol in normalized_wire, f"Missing wire contract: {symbol}"

for port in ["7240", "8240", "9240", "9241", "9242", "9340", "7200", "8200", "9200", "9201", "9202", "9300"]:
    assert port in connect, f"Missing channel port: {port}"

print("PASS: public API, six channels, authentication/data IDs and both port sets are present")
