from fastapi import FastAPI
from fastapi.responses import HTMLResponse, PlainTextResponse
import subprocess, time, os, datetime

app = FastAPI()

# --- runtime state ----------------------------------------------------------
start_time      = None     # disaster start
recovered       = False
last_backup_ts  = None
last_disaster_ts= None
last_restore_ts = None
# ---------------------------------------------------------------------------

def now_str():
    return datetime.datetime.now().strftime("%H:%M:%S")

# ---------------------------------------------------------------------------
@app.get("/")
def home():
    with open("web-ui.html") as f:
        return HTMLResponse(f.read())

# ---------------------------------------------------------------------------
@app.get("/backup")
def create_backup():
    global last_backup_ts
    subprocess.run(["bash", "backup.sh"])
    last_backup_ts = now_str()
    return {"status": "Backup created."}

# ---------------------------------------------------------------------------
@app.get("/disaster")
def trigger_disaster():
    global start_time, recovered, last_disaster_ts
    start_time = time.time()
    recovered = False
    last_disaster_ts = now_str()

    subprocess.run(["docker", "stop", "postgres-db"])
    subprocess.run(["docker", "rm", "postgres-db"])
    time.sleep(3)                               # let Docker clean up
    subprocess.run(["docker", "volume", "rm", "-f", "dr-simulator_pgdata"])

    return {"status": "Disaster triggered. DB volume deleted."}

# ---------------------------------------------------------------------------
@app.get("/restore")
def restore_backup():
    global recovered, last_restore_ts
    subprocess.run(["bash", "restore.sh"])
    recovered        = True
    last_restore_ts  = now_str()
    rto_value        = round(time.time() - start_time, 2) if start_time else None

    return {"status": "Restored!", "rto_seconds": rto_value or "N/A"}

# ---------------------------------------------------------------------------
@app.get("/status")
def status():
    # is container up?
    ps  = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", "postgres-db"],
                         capture_output=True, text=True)
    state_flag = ps.stdout.strip()
    state_txt  = "Running" if state_flag == "true" else "Stopped"

    rto_curr = None
    if recovered and start_time:
        rto_curr = round(time.time() - start_time, 2)
    elif start_time and not recovered:
        rto_curr = round(time.time() - start_time, 2)

    return {
        "container"     : "postgres-db",
        "state"         : state_txt,
        "dr_strategy"   : "Backup & Restore",
        "rto"           : rto_curr,
        "last_backup"   : last_backup_ts,
        "last_disaster" : last_disaster_ts,
        "last_restore"  : last_restore_ts
    }

# ---------------------------------------------------------------------------
@app.get("/logs")
def get_logs():
    """
    Return the last 50 lines from the postgres‑db container
    so the UI’s ‘nerd log’ has something to show.
    """
    try:
        raw = subprocess.check_output(
            ["docker", "logs", "--tail", "50", "postgres-db"],
            stderr=subprocess.STDOUT
        )
        return PlainTextResponse(raw.decode())
    except subprocess.CalledProcessError as e:
        return PlainTextResponse("⚠️  No logs yet – container may be down.", status_code=200)
