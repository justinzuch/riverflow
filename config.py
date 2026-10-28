"""All site configuration lives here. Edit this file to add/remove/reorder rivers."""
import os

# How long (seconds) to cache upstream data in memory. Gauges report every 15 min.
CACHE_SECONDS = int(os.environ.get("RIVERFLOW_CACHE_SECONDS", 15 * 60))
# 7-day history (sparkline) changes slowly; cache it longer.
HISTORY_CACHE_SECONDS = int(os.environ.get("RIVERFLOW_HISTORY_CACHE_SECONDS", 60 * 60))
SHOW_SPARKLINES = os.environ.get("RIVERFLOW_SPARKLINES", "1") == "1"

LOCAL_TZ = "America/Denver"
HTTP_TIMEOUT = 20
USER_AGENT = "flyfishlife.com riverflow (+https://flyfishlife.com/riverflow)"

# river = short name shown on the selector; water = river/water body subtitle
# source = "usgs": USGS Water Services instantaneous values, site_id = USGS site number
# source = "dwr":  Colorado Division of Water Resources telemetry, site_id = DWR station abbrev
SITES = [
    {
        "key": "deckers",
        "river": "Deckers",
        "water": "South Platte River",
        "source": "usgs",
        "site_id": "06701900",
        "gauge_name": "South Platte River below Brush Creek near Trumbull, CO (USGS 06701900)",
        "url": "https://waterdata.usgs.gov/monitoring-location/USGS-06701900/",
    },
    {
        "key": "dreamstream",
        "river": "Dream Stream",
        "water": "South Platte River",
        "source": "dwr",
        "site_id": "PLAHARCO",
        "gauge_name": "South Platte River above Elevenmile Reservoir near Hartsel, CO (DWR PLAHARCO / USGS 06695000)",
        "url": "https://dwr.state.co.us/Tools/Stations/PLAHARCO",
    },
    {
        "key": "elevenmile",
        "river": "Elevenmile Canyon",
        "water": "South Platte River",
        "source": "dwr",
        "site_id": "PLAGEOCO",
        "gauge_name": "South Platte River near Lake George, CO (DWR PLAGEOCO / USGS 06696000)",
        "url": "https://dwr.state.co.us/Tools/Stations/PLAGEOCO",
    },
    {
        "key": "pueblo",
        "river": "Arkansas below Pueblo",
        "water": "Arkansas River",
        "source": "dwr",
        "site_id": "ARKPUECO",
        "gauge_name": "Arkansas River above Pueblo, CO – just below Pueblo Dam (DWR ARKPUECO / USGS 07099400)",
        "url": "https://dwr.state.co.us/Tools/Stations/ARKPUECO",
        # Alternative (used by RiverReports): Moffat St in town, below the city intakes:
        # "source": "usgs", "site_id": "07099970",
        # "gauge_name": "Arkansas River at Moffat Street at Pueblo, CO (USGS 07099970)",
        # "url": "https://waterdata.usgs.gov/monitoring-location/USGS-07099970/",
    },
]
