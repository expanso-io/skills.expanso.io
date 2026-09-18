# Sensor telemetry over MQTT

Subscribe to sensor topics over MQTT, normalize readings (F to C), raise threshold alerts and keep malformed readings out of the telemetry stream.

**Use it when you are asked to build:** Sensor or industrial telemetry over MQTT: subscribe, normalize, alert.

## Where it was proven

Run on 2026-09-18 with `expanso-edge v2.1.21` on a **local-mode node only** (6/6 checks). It has not been run through Cloud.

Proved:

- 30 synthetic readings: 28 valid in telemetry, 3 alerts, 2 malformed rejected with the reason.

Not proved:

- Any run through Cloud; OPC UA, Modbus or any other industrial protocol; real sensor hardware. The publisher was a synthetic script.

## Components

- inputs: `mqtt`
- processors: `mapping`
- outputs: `switch`, `file`

## Files

- `pipeline.yaml`
- `publish.py`
- `skill.yaml`

Each `pipeline*.yaml` header lists the values to edit for your environment.

## Set up the dependencies

```bash
printf 'listener 1883\nallow_anonymous true\n' >mosquitto.conf
docker run -d --name mosquitto \
  -p 127.0.0.1:1883:1883 \
  -v "$PWD/mosquitto.conf:/mosquitto/config/mosquitto.conf" \
  eclipse-mosquitto:2
mkdir -p /var/tmp/expanso-telemetry
# after the job is running:
uv run -s publish.py 127.0.0.1 1883
```

## Validate, deploy, confirm

These commands deploy through your Expanso Cloud profile. This job was proven only on a local-mode node, so a Cloud run of it is untested.

```bash
expanso-edge validate pipeline.yaml
expanso-cli job validate pipeline.yaml --offline
expanso-cli job deploy pipeline.yaml
expanso-cli job describe sensor-telemetry
expanso-cli execution list --job-id <job-id>
```

A deploy only stores the job. Count the output where it lands:

```bash
# 28 readings and 3 alerts for the sample publisher:
wc -l /var/tmp/expanso-telemetry/telemetry.jsonl
wc -l /var/tmp/expanso-telemetry/alerts.jsonl
```

## Running it on Expanso Cloud

- The spec pins itself with an example `selector`. Label the node that can reach the job's dependencies to match, or change the selector. Use underscores, not hyphens, in label keys: a hyphenated key made the pipeline fail to build on the node.
- For a one-shot job, add `restart_policy: never` at the top level. With the default policy a failing bounded job was re-run every few seconds and read `running`; with `never` it ended `failed` after one execution.
- Paths, hosts and credentials resolve on the node that executes the job, not on the machine that deployed it.
