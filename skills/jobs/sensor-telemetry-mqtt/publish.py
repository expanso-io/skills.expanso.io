# /// script
# requires-python = ">=3.11"
# dependencies = ["paho-mqtt>=2"]
# ///
"""SYNTHETIC sensor publisher (independent of Expanso). Publishes 30 readings:
3 sensors x 10, QoS 1. Readings 3, 6, 9 of sensor-b exceed 80 C; readings 5
and 10 of sensor-c omit temp_f (malformed). Usage: publish.py HOST PORT"""

import json
import sys
import paho.mqtt.client as mqtt

host, port = sys.argv[1], int(sys.argv[2])
c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="jfp-synthetic-publisher")
c.connect(host, port)
c.loop_start()
for seq in range(1, 11):
    for sensor, line in (
        ("sensor-a", "line1"),
        ("sensor-b", "line1"),
        ("sensor-c", "line2"),
    ):
        temp_f = (
            150.0 + 20 * (seq % 3 == 0 and sensor == "sensor-b") * 3.5
            if sensor == "sensor-b"
            else 68.0 + seq
        )
        body = {
            "seq": seq,
            "ts": f"2026-09-17T12:{seq:02d}:00Z",
            "temp_f": round(temp_f, 1),
            "pressure_kpa": 101 + seq,
        }
        if sensor == "sensor-c" and seq % 5 == 0:
            del body["temp_f"]
        c.publish(
            f"plant/{line}/{sensor}/telemetry", json.dumps(body), qos=1
        ).wait_for_publish()
c.loop_stop()
c.disconnect()
print("published 30")
