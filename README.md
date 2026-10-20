# Gremlin Tank Monitor for Home Assistant

A Home Assistant integration for [GREMLIN](https://gremlinmonitors.com/)
propane and heating-oil tank monitors (Angus Energy). It reads the same data
as the **GREMLIN Tank Monitoring** mobile app: tank level, gallons,
delivery dates.

> **Unofficial.** Angus publishes no API. This integration uses the private
> backend of the consumer app, which can change without notice. It is not
> affiliated with or endorsed by Angus Energy or your fuel dealer. GREMLIN and
> its logo are trademarks of Angus Monitoring Service, used here only to
> identify the devices this integration works with.

## Installation (HACS)

1. HACS → ⋮ → **Custom repositories** → add `https://github.com/WStameris4/ha-gremlin`,
   category **Integration**.
2. Download **Gremlin Tank Monitor**, then restart Home Assistant.
3. Settings → Devices & services → **Add integration** → *Gremlin Tank Monitor*.
4. Sign in with the username and password you use in the GREMLIN app.

## What you get

One device per tank on the account, with these sensors:

| Sensor | Notes |
|---|---|
| Level | Percent full |
| Volume | Gallons in the tank |
| Capacity | Tank size in gallons (diagnostic) |
| Last reading | Date of the latest daily reading |
| Last delivery | Date of the last fuel delivery |
| Next delivery estimate | Your dealer's forecast |

Monitors report **once a day**, so the integration polls every 3 hours. Readings
are calendar dates, so the date sensors carry no time of day.

Tanks added to the account later appear after reloading the integration. If the
password changes, Home Assistant prompts you to re-authenticate.

## How it works

On each poll it signs in, lists the account's tanks, and reads the last 7 days
of levels for each one. Your credentials are stored in the Home Assistant
config entry and sent only to the GREMLIN service.
