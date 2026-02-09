"""
openvix.py

Creates an OpenViX/Enigma2 "recording-like" set from an MP4:
  - <name>.ts
  - <name>.eit
  - <name>.ts.meta
  - <name>.ts.cuts

It uses and needs installed on path:
  - ffmpeg  (to create the TS)
  - ffprobe (to read duration)

Copyright 2026 Pete Rai
https://github.com/pete-rai/enigma2-vod

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Usage:

  from openvix import vix
  vix(
    ".",                # outdir
    "video.mp4",        # inputFile
    "12 Angry Men",     # name
    "1957 drama",       # shortDesc
    "A jury of twelve men must decide the fate of ...",  # longDesc
    1957                # year
  )
"""

import os
import sys
import struct
import subprocess
import re
from datetime import datetime

# --- constant defaults

CHANNEL = "Xanadu"
LANG = "eng"
MODE = "copy"  # copy | h264 | hevc

# --- die with a message

def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)

# --- spawn helper

def run_or_die(cmd, args):
    try:
        result = subprocess.run([cmd] + args, check=True)
    except FileNotFoundError:
        die(f"Failed to run {cmd}: command not found")
    except subprocess.CalledProcessError as e:
        die(f"{cmd} exited with code {e.returncode}")

# --- BCD converter needed for DVB info

def to_bcd(n):
    if not isinstance(n, int) or n < 0 or n > 99:
        raise ValueError(f"BCD out of range: {n}")
    return ((n // 10) << 4) | (n % 10)

# --- convert gregorian date to modified julian date

def mjd_from_date(dt):
    y = dt.year
    m = dt.month
    d = dt.day
    a = (14 - m) // 12
    y2 = y + 4800 - a
    m2 = m + 12 * a - 3
    jdn = (
        d +
        (153 * m2 + 2) // 5 +
        365 * y2 +
        y2 // 4 -
        y2 // 100 +
        y2 // 400 -
        32045
    )

    mjd = jdn - 2400001
    return mjd & 0xffff

# --- utf8 text encoder

def enc_text(s):
    return str(s or "").encode("utf-8")

# --- DVB descriptor: short_event_descriptor (0x4D)

def short_event_descriptor(lang3, title, text):
    if not lang3 or len(lang3) != 3:
        raise ValueError("lang must be 3 letters (e.g., eng)")

    t = enc_text(title)
    x = enc_text(text)

    if len(t) > 255 or len(x) > 255:
        raise ValueError("short_event title/text max 255 bytes each")

    payload = b"".join([
        lang3.encode("ascii"),
        bytes([len(t)]),
        t,
        bytes([len(x)]),
        x,
    ])

    return bytes([0x4d, len(payload)]) + payload

# --- DVB descriptor: extended_event_descriptor (0x4E) with optional splitting

def extended_event_descriptors(lang3, long_text):
    if not long_text:
        return []
    if not lang3 or len(lang3) != 3:
        raise ValueError("lang must be 3 letters (e.g., eng)")

    full = enc_text(long_text)
    max_text = 255

    chunks = []
    for off in range(0, len(full), max_text):
        chunks.append(full[off:min(len(full), off + max_text)])

    last = len(chunks) - 1
    descriptors = []
    for idx, chunk in enumerate(chunks):
        descriptor_number = idx & 0x0f
        last_number = last & 0x0f
        dn = ((descriptor_number << 4) | last_number) & 0xff
        items = b""
        payload = b"".join([
            bytes([dn]),
            lang3.encode("ascii"),
            bytes([len(items)]),
            items,
            bytes([len(chunk)]),
            chunk,
        ])
        descriptors.append(bytes([0x4e, len(payload)]) + payload)

    return descriptors

# --- build enigma2 openvix sidecar .eit: event header (12 bytes) + descriptors loop

def build_sidecar_eit(
    event_id=1,
    start_unix=None,
    duration_seconds=None,
    title=None,
    short_desc=None,
    long_desc=None,
    lang3="eng",
):
    if not isinstance(event_id, int) or event_id < 0 or event_id > 0xffff:
        raise ValueError("eventId 0..65535")
    if start_unix is None or not isinstance(start_unix, (int, float)):
        raise ValueError("startUnix required")
    if duration_seconds is None or not isinstance(duration_seconds, (int, float)) or duration_seconds < 0:
        raise ValueError("durationSeconds required")

    # Handle negative timestamps (pre-1970) on Windows
    from datetime import timedelta
    start = datetime(1970, 1, 1) + timedelta(seconds=start_unix)
    mjd = mjd_from_date(start)

    st_h = start.hour
    st_m = start.minute
    st_s = start.second

    du_h = int(duration_seconds // 3600)
    du_m = int((duration_seconds % 3600) // 60)
    du_s = int(duration_seconds % 60)
    if du_h > 99:
        raise ValueError("duration too long (HH > 99)")

    descs = b"".join([
        short_event_descriptor(lang3, title, short_desc or ""),
        *extended_event_descriptors(lang3, long_desc or ""),
    ])

    desc_len = len(descs)
    if desc_len > 0x0fff:
        raise ValueError("descriptor loop too long (>4095 bytes)")

    # 16-bit flags: running_status(3) | free_CA_mode(1) | descriptors_loop_length(12)
    running_status = 4  # "running" (fine for sidecar usage)
    free_ca = 0
    flags = ((running_status & 0x7) << 13) | ((free_ca & 0x1) << 12) | (desc_len & 0x0fff)

    header = struct.pack(
        ">HHBBBBBBH",
        event_id & 0xffff,
        mjd & 0xffff,
        to_bcd(st_h),
        to_bcd(st_m),
        to_bcd(st_s),
        to_bcd(du_h),
        to_bcd(du_m),
        to_bcd(du_s),
        flags & 0xffff,
    )

    return header + descs

# --- get duration in seconds using ffprobe

def ffprobe_duration_seconds(file):
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=nk=1:nw=1",
                file,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError:
        die("Failed to run ffprobe: command not found")
    except subprocess.CalledProcessError as e:
        die(f"ffprobe exited with code {e.returncode}")

    s = result.stdout.strip()
    try:
        dur = float(s)
    except ValueError:
        die(f'Could not parse duration from ffprobe output: "{s}"')

    return max(0, round(dur))

# --- main function to create openvix recording-like set from an mp4

def vix(outdir, input_file, name, short_desc, long_desc, year):
    title = name[4:] + ", The" if name.startswith("The ") else name

    safe_name = str(name)
    safe_name = re.sub(r'\.{3,}', '-', safe_name)  # no ... ellipses (3+ dots)
    safe_name = (
        safe_name
        .replace("/", "-").replace("\\", "-").replace(":", "-")
        .replace("?", "-").replace("*", "-").replace('"', "-")
        .replace("<", "-").replace(">", "-").replace("|", "-")  # common unsafe chars
        .strip(". ")  # trim leading/trailing dots/spaces
    )
    # collapse multiple dashes
    safe_name = re.sub(r'-+', '-', safe_name)
    safe_name = safe_name.strip()

    input_path = os.path.join(outdir, input_file)
    base_name = f"{year}0101 0000 - {CHANNEL} - {safe_name}"
    out_ts = os.path.join(outdir, f"{base_name}.ts")
    out_meta = f"{out_ts}.meta"
    out_cuts = f"{out_ts}.cuts"
    out_eit = os.path.join(outdir, f"{base_name}.eit")

    # --- 1. Create TS

    if not os.path.exists(outdir):
        die(f"Output directory not found: {outdir}")

    if MODE == "copy":
        run_or_die("ffmpeg", ["-y", "-i", input_path, "-c", "copy", "-f", "mpegts", out_ts])
    elif MODE == "h264":
        run_or_die("ffmpeg", [
            "-y", "-i", input_path,
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.1",
            "-c:a", "aac", "-b:a", "192k", "-ac", "2",
            "-f", "mpegts",
            out_ts,
        ])
    elif MODE == "hevc":
        run_or_die("ffmpeg", [
            "-y", "-i", input_path,
            "-c:v", "libx265", "-pix_fmt", "yuv420p", "-tag:v", "hvc1",
            "-c:a", "aac", "-b:a", "192k", "-ac", "2",
            "-f", "mpegts",
            out_ts,
        ])
    else:
        die('Invalid --mode. Use "copy", "h264", or "hevc".')

    # --- 2. Calculate duration + filesize and write .meta

    start_dt = datetime(year, 1, 1, 0, 0, 0)
    start_unix = int((start_dt - datetime(1970, 1, 1)).total_seconds())
    dur_sec = ffprobe_duration_seconds(out_ts)
    size_bytes = os.path.getsize(out_ts)
    length_pts = dur_sec * 90000  # for openvix meta length is in PTS ticks (90kHz), not seconds

    # minimal "10-line style" like real recordings:
    # 1 serviceRef::ChannelName
    # 2 title
    # 3 description
    # 4 start time (unix)
    # 5 blank tags
    # 6 length (PTS ticks)
    # 7 filesize (bytes)
    # 8 service data (optional; blank is OK)
    # 9 packet size 188
    # 10 scrambled 0

    service_ref = f"1:0:0:0:0:0:0:0:0:0::{CHANNEL}"

    meta_text = (
        f"{service_ref}\n"
        f"{title}\n"
        f"\n"
        f"{start_unix}\n"
        f"\n"
        f"{length_pts}\n"
        f"{size_bytes}\n"
        f"\n"
        f"188\n"
        f"0\n"
    )

    with open(out_meta, "w", encoding="utf-8") as f:
        f.write(meta_text)

    # --- 3. Write .eit (sidecar)

    eit_bytes = build_sidecar_eit(
        event_id=1,
        start_unix=start_unix,
        duration_seconds=dur_sec,
        title=title,
        short_desc=short_desc,
        long_desc=long_desc,
        lang3=LANG,
    )
    with open(out_eit, "wb") as f:
        f.write(eit_bytes)

    # --- 4. write .cuts (empty with offset=0, cut type=3)

    buff = struct.pack(">QI", 0, 3)  # offset = start of content - big-endian 64-bit, cut type = 3 - big-endian 32-bit
    with open(out_cuts, "wb") as f:
        f.write(buff)

    print("  TS:   ", out_ts)
    print("  META: ", out_meta)
    print("  EIT:  ", out_eit)
    print("  CUTS: ", out_cuts)

    return base_name

# --- test call, only when run directly (not imported as a module)

if __name__ == "__main__":
    vix(
        ".",
        "video.mp4",
        "12 Angry Men",
        "1957 drama",
        "A jury of twelve men must decide the fate of a young man accused of murder.",
        1957
    )
