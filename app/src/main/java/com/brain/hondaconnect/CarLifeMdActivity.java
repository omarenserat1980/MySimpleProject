package com.brain.hondaconnect;

import android.app.Activity;
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

    private void refresh() {
        boolean nativeReady = CarLifeNativeLoader.load(this);
        StringBuilder out = new StringBuilder();
        out.append("Native library: ").append(nativeReady ? "LOADED" : "NOT LOADED").append('\n');
        if (!nativeReady) out.append("Loader: ").append(CarLifeNativeLoader.error()).append('\n');
        out.append("\nTransport status: NOT CONNECTED\n");
        out.append("Session / authentication / media JNI: NOT IMPLEMENTED YET\n\n");
        out.append("USB discovery\n");
        UsbManager manager = (UsbManager) getSystemService(USB_SERVICE);
        HashMap<String, UsbDevice> devices = manager.getDeviceList();
        if (devices.isEmpty()) out.append("No USB device currently enumerated. Connect the HU with a data-capable USB cable.\n");
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
        out.append("\nThis screen only enumerates descriptors; it does not claim a CarLife handshake or video/audio streaming.");
        report.setText(out.toString());
    }
}
