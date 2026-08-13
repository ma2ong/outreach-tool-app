"""Wait for the running backfill, then re-read every lead that still has no opening line.

The third pass is running the old code. Link-following and the widened Korean vocabulary
landed after it started, so the leads it writes off as "nothing on this site" were judged
by rules that could not see a Cafe24 navigation shell or the word 통합제어. Clearing
recheck_count for anything still without a hook gives those sites one read under the new
rules — and only those: a lead that already earned an opening line is left alone.

One-off, driven by a code change rather than by the calendar. Not part of the app.
"""
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.db import connect
from app.main_deps import DB_PATH

WAIT_FOR_PID = int(sys.argv[1]) if len(sys.argv) > 1 else 0


def alive(pid: int) -> bool:
    out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"],
                         capture_output=True, text=True).stdout
    return str(pid) in out


if WAIT_FOR_PID:
    while alive(WAIT_FOR_PID):
        time.sleep(20)

conn = connect(DB_PATH)
reset = conn.execute(
    "UPDATE leads SET recheck_count=0"
    " WHERE COALESCE(hook,'')='' AND COALESCE(recheck_count,0)>0"
    "   AND COALESCE(website,'')!=''").rowcount
conn.commit()
conn.close()
print(f"[chain] 新逻辑上线，重置 {reset} 家等待重读", flush=True)

subprocess.run([sys.executable, "-m", "app.backfill_brief", "--all"],
               cwd=os.path.dirname(os.path.abspath(__file__)))
