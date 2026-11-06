package com.brain.hondaconnect;

import android.app.Activity;
import android.hardware.usb.UsbAccessory;
import android.hardware.usb.UsbDevice;
import android.hardware.usb.UsbEndpoint;
import android.hardware.usb.UsbInterface;
import android.hardware.usb.UsbManager;
import android.os.Bundle;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import java.util.HashMap;

/** Phone-side MD diagnostics: native library load and USB descriptor discovery. */
public class CarLifeMdActivity extends Activity {
    private static final String BUILD_ID = "md-usb-accessory-probe-20261106-r3";
    private TextView report;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(28, 28, 28, 28);
        TextView title = new TextView(this);
        title.setText("CarLife MD · Phone Sender");
        title.setTextSize(22);
        root.addView(title);
        report = new TextView(this);
        report.setTextIsSelectable(true);
        report.setPadding(0, 20, 0, 20);
        root.addView(report, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1));
        Button scan = new Button(this);
        scan.setText("فحص USB وإعادة تحميل مكتبة MD");
        root.addView(scan);
        setContentView(root);
        scan.setOnClickListener(v -> refresh());
        refresh();
    }

    private void appendNetworkDiagnostics(StringBuilder out) {
        out.append("\nMD network diagnostics (read-only)\n");
        try {
            android.net.ConnectivityManager cm =
                (android.net.ConnectivityManager) getSystemService(CONNECTIVITY_SERVICE);
            android.net.Network active = cm == null ? null : cm.getActiveNetwork();
            if (active == null) {
                out.append("Active network: NONE\n");
            } else {
                out.append("Active network: PRESENT\n");
                android.net.NetworkCapabilities caps = cm.getNetworkCapabilities(active);
                if (caps != null) {
                    out.append("Transports:");
                    if (caps.hasTransport(android.net.NetworkCapabilities.TRANSPORT_WIFI)) out.append(" WIFI");
                    if (caps.hasTransport(android.net.NetworkCapabilities.TRANSPORT_CELLULAR)) out.append(" CELLULAR");
                    if (caps.hasTransport(android.net.NetworkCapabilities.TRANSPORT_ETHERNET)) out.append(" ETHERNET");
                    if (caps.hasTransport(android.net.NetworkCapabilities.TRANSPORT_BLUETOOTH)) out.append(" BLUETOOTH");
                    if (caps.hasTransport(android.net.NetworkCapabilities.TRANSPORT_VPN)) out.append(" VPN");
                    out.append("\nValidated internet: ").append(caps.hasCapability(
                        android.net.NetworkCapabilities.NET_CAPABILITY_VALIDATED)).append('\n');
                }
                android.net.LinkProperties lp = cm.getLinkProperties(active);
                if (lp != null) {
                    out.append("Active interface: ").append(lp.getInterfaceName()).append('\n');
                    out.append("Active link addresses: ");
                    for (android.net.LinkAddress address : lp.getLinkAddresses()) {
                        out.append(address.getAddress().getHostAddress()).append(' ');
                    }
                    out.append('\n');
                    out.append("Active routes: ");
                    for (android.net.RouteInfo route : lp.getRoutes()) {
                        out.append(route.toString()).append(" | ");
                    }
                    out.append('\n');
                    out.append("DNS: ");
                    for (java.net.InetAddress dns : lp.getDnsServers()) {
                        out.append(dns.getHostAddress()).append(' ');
                    }
                    out.append('\n');
                } else {
                    out.append("Active link properties: UNAVAILABLE\n");
                }
            }
        } catch (SecurityException error) {
            out.append("Connectivity permission error: ").append(error.getMessage()).append('\n');
        } catch (Throwable error) {
            out.append("Connectivity diagnostic error: ").append(error.getClass().getSimpleName())
               .append(": ").append(error.getMessage()).append('\n');
        }

        try {
            java.util.Enumeration<java.net.NetworkInterface> interfaces =
                java.net.NetworkInterface.getNetworkInterfaces();
            if (interfaces == null) {
                out.append("Interface enumeration: UNAVAILABLE\n");
                return;
            }
            while (interfaces.hasMoreElements()) {
                java.net.NetworkInterface nif = interfaces.nextElement();
                out.append("Interface ").append(nif.getName())
                   .append(" up=").append(nif.isUp())
                   .append(" loopback=").append(nif.isLoopback())
                   .append(" mtu=").append(nif.getMTU()).append(" addresses=");
                java.util.Enumeration<java.net.InetAddress> addresses = nif.getInetAddresses();
                while (addresses.hasMoreElements()) {
                    java.net.InetAddress address = addresses.nextElement();
                    out.append(address.getHostAddress());
                    if (address instanceof java.net.Inet6Address) out.append("(IPv6)");
                    out.append(' ');
                }
                out.append('\n');
            }
        } catch (Throwable error) {
            out.append("Interface enumeration error: ").append(error.getClass().getSimpleName())
               .append(": ").append(error.getMessage()).append('\n');
        }
    }

    private void refresh() {
        StringBuilder out = new StringBuilder();
        out.append("MD build: ").append(BUILD_ID).append("\n");
        try {
            android.content.pm.PackageInfo info = getPackageManager().getPackageInfo(getPackageName(), 0);
            out.append("App version: ").append(info.versionName)
               .append(" (").append(info.getLongVersionCode()).append(")\n");
            out.append("APK source: ").append(getApplicationInfo().sourceDir).append('\n');
            out.append("Native dir: ").append(getApplicationInfo().nativeLibraryDir).append('\n');
            out.append("ABIs: ").append(java.util.Arrays.toString(android.os.Build.SUPPORTED_ABIS)).append('\n');
        } catch (Exception metadataError) {
            out.append("App metadata error: ").append(metadataError.getClass().getSimpleName()).append('\n');
        }
        appendNetworkDiagnostics(out);
        boolean nativeReady = CarLifeNativeLoader.load(this);
        out.append("Native library: ").append(nativeReady ? "LOADED" : "NOT LOADED").append('\n');
        if (!nativeReady) out.append("Loader: ").append(CarLifeNativeLoader.error()).append('\n');

        boolean jniReady = false;
        int probeResult = -1;
        String jniError = "";
        if (nativeReady) {
            try {
                probeResult = CarLifeJni.nativeBridgeProbe();
                jniReady = probeResult == CarLifeJni.BRIDGE_PROBE_OK;
                if (!jniReady) jniError = "Unexpected JNI probe value: 0x" + Integer.toHexString(probeResult);
            } catch (Throwable error) {
                jniError = error.getClass().getSimpleName() + ": " + error.getMessage();
            }
        } else {
            jniError = CarLifeNativeLoader.error();
        }
        out.append("JNI bridge: ").append(jniReady ? "CALLABLE" : "NOT VERIFIED").append('\n');
        out.append("JNI probe: ").append(probeResult < 0 ? "NOT RUN" : "0x" + Integer.toHexString(probeResult)).append('\n');
        if (!jniReady) out.append("JNI diagnostic: ").append(jniError).append('\n');

        int initResult = -1;
        if (jniReady) {
            try {
                initResult = CarLifeJni.nativeInitialize();
            } catch (Throwable error) {
                out.append("Native init exception: ").append(error.getClass().getSimpleName())
                   .append(": ").append(error.getMessage()).append('\n');
            }
        }
        out.append("Native library init: ").append(initResult == 0 ? "PASS" : "NOT VERIFIED (" + initResult + ")").append('\n');
        out.append("Transport status: NOT CONNECTED\n");
        out.append("CarLife connection setup is intentionally not invoked until MD IP/interface are verified.\n");
        out.append("Authentication / active session / video / audio: NOT IMPLEMENTED YET\n\n");
        out.append("USB transport diagnostics (read-only)\n");
        UsbManager manager = (UsbManager) getSystemService(USB_SERVICE);
        if (manager == null) {
            out.append("UsbManager: UNAVAILABLE\n");
        } else {
            UsbAccessory[] accessories = manager.getAccessoryList();
            if (accessories == null || accessories.length == 0) {
                out.append("USB accessory: NONE ENUMERATED\n");
            } else {
                for (int i = 0; i < accessories.length; i++) {
                    UsbAccessory accessory = accessories[i];
                    out.append("\nUSB accessory ").append(i)
                       .append("\nManufacturer: ").append(accessory.getManufacturer())
                       .append("\nModel: ").append(accessory.getModel())
                       .append("\nDescription: ").append(accessory.getDescription())
                       .append("\nVersion: ").append(accessory.getVersion())
                       .append("\nURI: ").append(accessory.getUri())
                       .append("\nSerial: ").append(accessory.getSerial());
                }
            }
            HashMap<String, UsbDevice> devices = manager.getDeviceList();
            out.append("\nUSB host devices: ").append(devices.size()).append('\n');
            if (devices.isEmpty()) out.append("No USB host devices enumerated (this can be normal in accessory mode).\n");
            for (UsbDevice device : devices.values()) {
                out.append("\nDevice: ").append(device.getDeviceName())
                   .append("\nVID: 0x").append(Integer.toHexString(device.getVendorId()))
                   .append("  PID: 0x").append(Integer.toHexString(device.getProductId()))
                   .append("\nClass: ").append(device.getDeviceClass())
                   .append(" Subclass: ").append(device.getDeviceSubclass())
                   .append(" Protocol: ").append(device.getDeviceProtocol());
                for (int i = 0; i < device.getInterfaceCount(); i++) {
                    UsbInterface intf = device.getInterface(i);
                    out.append("\n  Interface ").append(i).append(": class=").append(intf.getInterfaceClass())
                       .append(" subclass=").append(intf.getInterfaceSubclass())
                       .append(" protocol=").append(intf.getInterfaceProtocol());
                    for (int e = 0; e < intf.getEndpointCount(); e++) {
                        UsbEndpoint ep = intf.getEndpoint(e);
                        out.append("\n    Endpoint ").append(e).append(": address=0x")
                           .append(Integer.toHexString(ep.getAddress())).append(" type=").append(ep.getType())
                           .append(" direction=").append(ep.getDirection()).append(" maxPacket=").append(ep.getMaxPacketSize());
                    }
                }
                out.append('\n');
            }
        }
        out.append("\nRead-only USB inspection only; no permission request, CarLife handshake, or media streaming was started.\n\n");
        report.setText(out.toString());
    }
}
