# CarLife MD protocol inventory — phone-side workstream

Scope: `omarenserat1980/MySimpleProject`, branch `brain/honda-android-network-sqlite`.
This document describes the pinned `CarLife-MD-Lib` API and wire identifiers inspected in source. It does **not** claim a live Honda handshake.

## Role separation

- MD / Phone sender: Android app in `MySimpleProject`; this is the current build target.
- HU / Vehicle receiver: Apollo DuerOS / `CarLife-Android-Vehicle-V2.0` in `ElectronicBrain-Simulator`; preserve its last successful APK and do not rebuild it as part of MD changes.
- Android Auto / HUR is not interchangeable with Baidu CarLife. Do not import AA protocol assumptions into this CarLife path.

## Public C++ API found in `CCarLifeLibWrapper.h`

| Area | API | Purpose |
|---|---|---|
| Lifecycle | `getInstance`, `carLifeLibInit`, `carLifeLibDestory`, `disconnect` | Singleton/init/reset |
| Setup | `connectionSetup()`, `connectionSetup(mdIP)`, `connectionSetup(mdIP, interfaceName)` | Open six channel sockets |
| CMD | `cmdReceiveOperation`, `cmdRegisterProtocolVersionMatchStatus`, `cmdRegisterMDInfro` | Command receive + callbacks |
| Authentication | `cmdHuAuthenRequest`, `cmdRegisterMdAuthenResponse`, `cmdHuAuthenResult`, `cmdRegisterMdAuthenResult` | HU↔MD authentication messages |
| Video | `videoReceiveOperation`, `videoRegisterDataReceive`, `videoRegisterHeartBeat` | Video payload + heartbeat |
| Media | `mediaReceiveOperation`, `mediaRegisterInit`, `mediaRegisterNormalData`, `mediaRegisterStop/Pause/Resume/Seek` | Audio stream lifecycle/data |
| CTRL | `ctrlReceiveOperation`, `ctrlTouchAction*`, `ctrlTouchCarHardKeyCode` | Touch and hard-key messages |
| VR/TTS | `vrReceiveOperation`, `sendVRRecordData`, `ttsReceiveOperation` | Separate voice channels |

The receive methods each perform a blocking header/data receive cycle and should be run on separate managed worker threads, never on the Android UI thread. Callbacks must copy transient native buffers before crossing JNI; never retain the library's raw pointer after callback return.

## Wire channel identifiers and message IDs

From `CTranRecvPackageProcess.h`:

| Channel | ID | Header | Maximum payload in this source |
|---|---:|---:|---:|
| CMD | 1 | 8 bytes | 40 KiB |
| VIDEO | 2 | 12 bytes | 600 KiB |
| MEDIA | 3 | 12 bytes | 100 KiB |
| TTS | 4 | 12 bytes | 50 KiB |
| VR | 5 | 12 bytes | 50 KiB |
| CTRL | 6 | 8 bytes | 10 KiB |

Important CMD messages:

| Message | ID |
|---|---:|
| HU protocol version | `0x00018001` |
| protocol match status | `0x00010002` |
| HU info | `0x00018003` |
| MD info | `0x00010004` |
| video encoder init / done | `0x00018007` / `0x00010008` |
| video encoder start / pause / reset | `0x00018009` / `0x0001800A` / `0x0001800B` |
| media pause | `0x0001800E` |
| media info / progress | `0x00010035` / `0x00010036` |
| HU auth request | `0x00018048` |
| MD auth response | `0x00010049` |
| HU auth result | `0x0001804A` |
| MD auth result | `0x0001004B` |

Data-channel messages:

- VIDEO: `MSG_VIDEO_DATA=0x00020001`, `MSG_VIDEO_HEARTBEAT=0x00020002`.
- MEDIA: `MSG_MEDIA_INIT=0x00030001`, STOP `0x00030002`, PAUSE `0x00030003`, RESUME `0x00030004`, SEEK `0x00030005`, DATA `0x00030006`.
- CTRL: touch action/down/up/move/single-click/double-click/long-press/hard-key = `0x00068001` through `0x00068008`; UI action sound `0x00060009`.

## Transport facts and unresolved role mapping

`connectionSetup()` calls `execSocketForward()` and then opens six sockets. The forward commands map host ports 7200/8200/9200/9201/9202/9300 to 7240/8240/9240/9241/9242/9340. This path depends on an `adb` executable/forwarding environment and is not suitable for an ordinary Android app without an explicit ADB transport.

`connectionSetup(mdIP, interfaceName)` avoids ADB and attempts TCP connections to the supplied IPv4/IPv6 address, binding through the named interface. Source constants label its destination ports as MD-side ports: 7240, 8240, 9240, 9241, 9242, 9340. The alternate local/HU ports are 7200, 8200, 9200, 9201, 9202, 9300. **Do not assume the Honda HU listens on either set until the Vehicle SDK/server source or a controlled packet capture confirms it.** This port-direction question is a hard gate before invoking native setup.

The socket setup opens CMD, VIDEO, MEDIA, TTS, VR, CTRL in sequence and returns on the first failure. It is not an atomic rollback in the inspected implementation; connection teardown/retry behavior needs testing before production use.

## Next implementation gates

1. Verify HU-side listener ports and transport discovery from `CarLife-Android-Vehicle-V2.0` source, not from Android Auto docs.
2. Implement Android USB permission/device-role inspection independently from network transport. USB enumeration alone is not CarLife transport.
3. Implement an explicit transport adapter (USB tether/network or documented USB bulk framing) and test reconnection/partial failures.
4. Add a session state machine: DISCOVERED → TRANSPORT_READY → CHANNELS_CONNECTED → VERSION_MATCHED → AUTH_PENDING → AUTHENTICATED → MEDIA_READY; every failure transitions to DISCONNECTED with socket cleanup.
5. Only after a simulated HU accepts the protocol should callback threads, touch mapping, video decode and audio playback be enabled.
