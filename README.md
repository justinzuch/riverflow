# River Flow – flyfishlife.com/riverflow

## Quick start (run it on your computer)

You need Python 3.9+ installed (python.org). Unzip the project, open a terminal **in the `riverflow` folder**, then:

**Windows (PowerShell or Command Prompt)**
```
py -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

**Mac / Linux (Terminal)**
```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:5000** in your browser. Press `Ctrl+C` in the terminal to stop.
Next time, you only need the `activate` line and `python app.py`.
(If PowerShell blocks `activate`, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.)

Pick a river with the buttons at the top. Each river has its own shareable link:
`?river=deckers`, `?river=dreamstream`, `?river=elevenmile`, `?river=pueblo` (or `#deckers` style). JSON is at `/api/flows`.

---

A small Flask app that shows **current streamflow (CFS)** for four Colorado fly-fishing rivers,
with a river selector, a 7-day chart (low/high, hover for values) and a JSON endpoint.

| River | Gauge | Source |
|---|---|---|
| Deckers | South Platte R. below Brush Creek near Trumbull (USGS **06701900**) | USGS Water Services |
| Dream Stream | South Platte R. above Elevenmile Reservoir near Hartsel (DWR **PLAHARCO** = USGS 06695000), between Spinney and Elevenmile | Colorado DWR telemetry |
| Elevenmile Canyon | South Platte R. near Lake George (DWR **PLAGEOCO** = USGS 06696000) | Colorado DWR telemetry |
| Arkansas below Pueblo | Arkansas R. above Pueblo (DWR **ARKPUECO** = USGS 07099400), just below Pueblo Dam | Colorado DWR telemetry |

Why two sources: the Dream Stream, Elevenmile and Pueblo dam gauges are operated by Colorado's Division of
Water Resources, and USGS no longer serves live data for them. Deckers is USGS-operated.
Current values use **one batched call per source** (2 calls total) and are cached in memory for 15 minutes.
7-day charts use one call per gauge, cached for 60 minutes.

## Files
```
app.py            Flask app: "/" page (river selector, ?river=<key>), "/api/flows" JSON, 7-day chart builder
flows.py          Fetching, parsing, caching (USGS + DWR)
config.py         <- all gauge settings live here (add/remove/reorder rivers)
passenger_wsgi.py Entry point for cPanel / Passenger
templates/index.html  Page + small vanilla JS (tab switching, shareable URL, chart hover)
static/style.css      Responsive styles (4 tabs on desktop, 2x2 grid on phones)
requirements.txt
```

## Run locally
See Quick start above. `python app.py` and `flask --app app run --debug` both serve http://127.0.0.1:5000/.
Set `PORT=8000` to use a different port with `python app.py`.

Optional environment variables:
- `RIVERFLOW_CACHE_SECONDS` (default 900)
- `RIVERFLOW_HISTORY_CACHE_SECONDS` (default 3600)
- `RIVERFLOW_SPARKLINES=0` to turn off the 7-day charts
- `RIVERFLOW_URL_PREFIX=/riverflow` only needed if your server passes the full path without setting SCRIPT_NAME (see troubleshooting)

## Push to GitHub
```bash
git init && git add . && git commit -m "River flow app"
git remote add origin git@github.com:<you>/riverflow.git && git push -u origin main
```
(`.gitignore` already excludes `venv/` and caches.)

## Deploy on GoDaddy cPanel (Setup Python App)
1. Upload the project: in cPanel **Terminal**, `git clone` your repo into your home directory, e.g. `~/riverflow`
   (or upload the zip with File Manager and extract). Keep it **outside** `public_html`.
2. cPanel → **Setup Python App** → **Create Application**:
   - Python version: 3.9 or newer (latest available)
   - Application root: `riverflow`
   - Application URL: `flyfishlife.com` / `riverflow`
   - Application startup file: `passenger_wsgi.py`
   - Application entry point: `application`
   - Click **Create**.
3. Install requirements: on the app page, add `requirements.txt` under "Configuration files" and click
   **Run Pip Install**. Or in Terminal, copy the "Enter to the virtual environment" command shown at the top
   of the app page, run it, then `pip install -r requirements.txt`.
4. Click **Restart**, then open https://flyfishlife.com/riverflow/ and https://flyfishlife.com/riverflow/api/flows.
5. To update later: `cd ~/riverflow && git pull`, then Restart the app (or `touch tmp/restart.txt`).

### Troubleshooting
- **CSS missing / links point to `/static`**: add environment variable `RIVERFLOW_URL_PREFIX=/riverflow`
  in the Setup Python App page and restart.
- **500 error**: check `~/riverflow/stderr.log` (Passenger) or the cPanel error log.
- **Outbound requests blocked**: shared hosting normally allows outbound HTTPS; if not, ask GoDaddy support.
- If a gauge goes offline, its card shows a "No current data" message instead of breaking the page.

## Data sources / notes
- USGS: `https://waterservices.usgs.gov/nwis/iv/?format=json&sites=06701900&parameterCd=00060`.
  USGS plans to retire Water Services in favor of the new Water Data APIs (api.waterdata.usgs.gov);
  if that happens, only `_fetch_usgs_current` / `_fetch_history` in `flows.py` need updating.
- DWR: `https://dwr.state.co.us/Rest/GET/api/v2/telemetrystations/telemetrystation/?format=json&abbrev=PLAGEOCO,ARKPUECO&parameter=DISCHRG`
  (anonymous use is rate-limited; the cache keeps this app far below limits).
- Pueblo gauge choice: DWR ARKPUECO, about 0.4 river miles below Pueblo Dam. It best represents the tailwater
  from the dam down to the Nature & Raptor Center (Rock Canyon), and DWR posts readings faster than USGS posts Moffat St.
  Between this gauge and the Nature Center the main changes are the Pueblo Fish Hatchery return (adds ~20 cfs) and the
  small West Pueblo Ditch / Comanche pump diversions. Pueblo Water Works' intakes are at or just below the Nature Center.
- Alternative: USGS 07099970 "Arkansas River at Moffat Street at Pueblo" is the gauge RiverReports uses for
  "Below Pueblo Reservoir" (https://www.riverreports.com/states/co/sites/3160ad77-7d5d-4a45-89d6-20a864243847).
  It is ~8 river miles downstream in town, below the city's water intakes, so it often reads lower and reacts to dam
  release changes later. To switch, edit the `pueblo` entry in `config.py`: set `source: "usgs"`, `site_id: "07099970"`
  and the commented-out gauge_name/url.
- Dream Stream: there is no live gauge directly below Spinney Mountain Dam. PLAHARCO sits on the Dream Stream about
  3.7 river miles below the dam, just above the Elevenmile inlet. (PLASPICO / USGS 06694920 is *above* Spinney, not the Dream Stream.)
- All data is provisional. Times shown in America/Denver (MDT/MST).
