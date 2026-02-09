# Enigma2 VOD Library System

> Visit my [Blog](http://pete.rai.org.uk) to get in touch or to
see demos of this and much more.

Transform your Enigma2 satellite receiver into a fully browsable Video-on-Demand library with rich metadata, cover art, and custom UI components.

## Overview

This project provides tools and components to convert standard MP4 video files into Enigma2-compatible "recording-like" media sets, complete with metadata, cover artwork, and custom skin renderers. The result is a native-feeling VOD experience that organizes your movie collection by genre, decade, country, theme, director, cast, and more - all browsable directly through your Enigma2 interface.

Instead of a flat list of recordings, you get a beautifully organized media library with descriptions, cover images, and intuitive navigation - turning your satellite receiver into a home theater system.

## Motivation

Enigma2 receivers are powerful devices with excellent playback capabilities, but they're typically limited to displaying recordings and basic file lists. This project was born from the desire to:

- **Leverage existing hardware**: Use your Enigma2 receiver as a complete media center without additional devices
- **Preserve the native experience**: Keep the familiar Enigma2 interface while adding rich media library features
- **Organize large collections**: Browse hundreds of films by meaningful categories
- **Add visual appeal**: Display cover art and detailed descriptions for each title
- **Maintain flexibility**: Use standard file formats and folder structures that remain accessible outside Enigma2

The system essentially tricks Enigma2 into thinking your movies are recordings, complete with proper metadata (`.eit` files), timeline information (`.cuts` files), and service references (`.meta` files) - all generated programmatically from your source video files.

For more context, see the discussion thread: [Turning Enigma2 into a fully browsable VOD library](https://world-of-satellite.com/threads/turning-enigma2-into-a-fully-browsable-vod-library.67535/)

## Repository Structure

### `/art` - Cover Artwork

This folder contains sample cover images organized by category. The structure mirrors the browsing hierarchy used in Enigma2:

- **`/cover`** - Individual movie posters _(excluded from this repository for copyright reasons)_
- **`/category`** - Category folder icons (genre, decade, country, etc.)
- **`/genre`** - Genre-specific artwork (action, drama, western, etc.)
- **`/country`** - Country/region cover images
- **`/decade`** - Decade-specific artwork (1920s through 2020s)
- **`/duration`** - Duration category images (short, standard, long, epic)
- **`/theme`** - Thematic artwork (redemption, war, love, etc.)
- **`/people`** - Actor and director portraits _(excluded from this repository for privacy reasons)_

All artwork should be PNG format. The system uses a smart fallback mechanism: if a specific cover isn't found, it attempts variations (with/without year suffixes), and ultimately falls back to a transparent placeholder.

> **Note**: People portraits (cast / director images) and movie cover art are not included in this repository to respect privacy and copyright.

#### Canvas and Aspect Ratio

The Enigma2 skin is designed for a **835×485 pixel** display area. To ensure artwork fits properly and maintains visual consistency, all cover images are composited onto a background canvas that matches this exact aspect ratio.

```python
import subprocess

canvas = "/path/to/art/canvas.png"
source = "/path/to/art/genre/western.png"
output = "/etc/xanadu/genre/western.png"

cmd = f'magick ( "{canvas}" -resize 835x485! ) ( "{source}" -resize x485 ) -gravity center -composite "{output}"'
subprocess.run(cmd, shell=True, check=True)
```

This command:
1. Resizes the canvas to exactly 835×485 pixels (forced with `!`)
2. Resizes the source artwork to fit the height (485px) while maintaining aspect ratio
3. Centers the artwork on the canvas using `-gravity center`
4. Composites the layers into the final output image

This ensures that all artwork, regardless of original dimensions, displays correctly within the Enigma2 interface without distortion or cropping issues.

### `/script` - Conversion Scripts

The conversion utilities create Enigma2-compatible file sets from standard MP4 videos:

#### `openvix.py` (Python version)
Python implementation that generates the complete Enigma2 recording set from an MP4 input:
- Creates `.ts` transport stream (via ffmpeg)
- Builds `.eit` sidecar with DVB event information (title, descriptions, duration)
- Generates `.ts.meta` with service reference and recording metadata
- Produces `.ts.cuts` file marking the last playback point of each recording - starts from zero

This script also:

- Handles pre-1970 dates correctly (important for classic films)
- Supports "The" prefix transformation (e.g., "The Godfather" → "Godfather, The")
- Sanitizes filenames for cross-platform compatibility
- Generates proper DVB/EIT binary structures with BCD encoding and MJD date conversion
- Supports multiple encoding modes: `copy` (fastest), `h264`, or `hevc`

**Requirements**:

`ffmpeg` and `ffprobe` must be installed and available on PATH.

**Usage**:
```python
from openvix import vix
vix(
    ".",                # output directory
    "video.mp4",        # input file
    "12 Angry Men",     # movie title
    "1957 drama",       # short description
    "A jury of twelve men must decide...",  # long description
    1957                # year
)
```
### `/skin` - Enigma2 Skin Components

#### `/Converter` - Data Converters

Enigma2 Converters transform data before it's displayed. Install to `/usr/lib/enigma2/python/Components/Converter/`:

**`FormatName.py`**
- Converts folder paths into human-readable breadcrumbs
- Transforms `/media/hdd/movie/Xanadu/Genre/Action` → `Genre - Action`
- Replaces `.Trash` with "Deleted Items"
- Shows "PVR Movie List" for root directory

**`FormatDescription.py`**
- Provides rich descriptions for folders and categories
- Loads metadata from `/etc/xanadu/db.json`
- Falls back gracefully if JSON is missing or invalid
- Returns custom text for special folders (e.g., "Welcome to the pleasure dome of classic cinema" for the Xanadu root)

**`FormatExtra.py`**
- Extracts additional information from service paths/filenames
- Filters content based on path patterns
- Returns empty string for non-matching items (keeps UI clean)

**`db.json`**
- Contains category descriptions used by `FormatDescription.py`
- Organized by: Genre, Decade, Duration, Country, Theme, and Xanadu categories
- Each entry provides a contextual, engaging description for folder navigation
- Deploy to `/etc/xanadu/db.json` on your Enigma2 device

#### `/Renderer` - UI Renderers

Renderers handle visual presentation. Install to `/usr/lib/enigma2/python/Components/Renderer/`:

**`CoverPixmap.py`**
- Displays cover art based on current selection
- Implements smart path resolution for folders vs. .ts files
- Normalizes movie titles to match cover filenames (handles accents, punctuation, etc.)
- Searches multiple candidate paths with year suffix variations
- Provides genre fallback for theme categories
- Logs missing artwork to `/tmp/coverpixmap_debug.log` for troubleshooting
- Hides widget if no cover image is found
- Handles special categories (cast/director use people portraits)

### Deployment

After copying the Python files to your Enigma2 device:

```bash
# Converters
chmod 644 /usr/lib/enigma2/python/Components/Converter/Format*.py
chown root:root /usr/lib/enigma2/python/Components/Converter/Format*.py

# Renderer
chmod 644 /usr/lib/enigma2/python/Components/Renderer/CoverPixmap.py
chown root:root /usr/lib/enigma2/python/Components/Renderer/CoverPixmap.py

# Database
chmod 644 /etc/xanadu/db.json
chown root:root /etc/xanadu/db.json
```

Restart Enigma2 for changes to take effect.

## Skin XML Integration Example

Here's how to integrate the custom components into your Enigma2 skin's `MovieSelection` screen. This example shows the complete screen definition with the custom converters and renderer in use:

```xml
<!-- ## MOVIESELECTION ## -->
<screen name="MovieSelection" position="fill" backgroundColor="transparent" flags="wfNoBorder" >
    <ePixmap pixmap="infobar/background.png" position="fill" alphatest="on" zPosition="-1"/>
    <widget source="Title" render="RunningText" options="movetype=running,startpoint=0,direction=left,steptime=140,repeat=3,always=0,oneshot=1,startdelay=6000,wrap" position="25,20" size="610,50" font="screentitle;40" foregroundColor="maincolour" backgroundColor="menubackground" halign="left" valign="center" transparent="1" zPosition="3" />
    <panel name="FullScreenTimeDate" />
    <widget source="Service" render="Picon" position="650,20" size="220,132" alphatest="blend" backgroundColor="transparent" transparent="1" zPosition="3">
        <convert type="MovieReference"/>
    </widget>
    <widget name="waitingtext" position="22,160" size="850,800" font="infobar2;36" foregroundColor="maincolour" backgroundColor="menubackground" halign="center" valign="center" transparent="1" zPosition="2" />
    <widget name="list" position="22,160" size="850,800" font="infobar2;32" itemHeight="60" pbarHeight="20" pbarLargeWidth="70" pbarColour="thirdcolour" pbarColourSeen="yellow" pbarColourRec="red" spaceIconeText="8" iconsWidth="37" spaceRight="5" dateWidth="1" foregroundColor="maincolour" backgroundColor="menubackground" transparent="1" enableWrapAround="1" scrollbarMode="showOnDemand" zPosition="3"  />
    <eLabel text="STORAGE" position="22,950" size="250,60" font="infobar2;32" foregroundColor="maincolour" backgroundColor="menubackground" transparent="1" halign="left" valign="center" zPosition="3"/>
    <widget name="freeDiskSpace" position="190,950" size="690,60" font="infobar2;32" foregroundColor="thirdcolour" backgroundColor="menubackground" transparent="1" halign="left" valign="center" zPosition="3" />
    <panel name="FullscreenPIGPanel" />

    <!-- Custom CoverPixmap Renderer - displays movie/folder artwork -->
    <widget source="Service" render="CoverPixmap" position="1005,90" size="835,485" alphatest="blend" zPosition="10" />

    <!-- Custom FormatName Converter - shows breadcrumb navigation -->
    <widget source="Service" render="RunningText" options="movetype=running,startpoint=0,direction=top,steptime=140,repeat=3,always=0,oneshot=1,startdelay=100000,wrap" position="1025,605" size="795,60" font="screentitle;38" foregroundColor="maincolour" backgroundColor="menubackground" transparent="1" halign="center" valign="top" zPosition="3">
        <convert type="MovieInfo">Name</convert>
        <convert type="FormatName"></convert>
    </widget>

    <!-- Custom FormatDescription Converter - shows category descriptions -->
    <widget source="Service" render="RunningText" options="movetype=running,startpoint=0,direction=top,steptime=140,repeat=3,always=0,oneshot=1,startdelay=100000,wrap" position="1025,675" size="795,165" font="infobar2;30" foregroundColor="maincolour" backgroundColor="menubackground" transparent="1" halign="center" valign="top" zPosition="3">
        <convert type="MovieInfo">MetaDescription</convert>
        <convert type="FormatDescription"></convert>
    </widget>

    <!-- Custom FormatExtra Converter - shows additional metadata -->
    <widget source="Service" render="RunningText" options="movetype=running,startpoint=0,direction=top,steptime=140,repeat=3,always=0,oneshot=1,startdelay=100000,wrap" position="1025,865" size="795,120" font="infobar2;28" foregroundColor="maincolour" backgroundColor="menubackground" transparent="1" halign="center" valign="top" zPosition="3">
        <convert type="MovieInfo">ShortDescription</convert>
        <convert type="FormatExtra"></convert>
    </widget>

    <widget name="TrashcanSize" position="1005,950" size="835,50" font="screentitle;38" foregroundColor="maincolour" backgroundColor="menubackground" transparent="1" halign="left" valign="center" zPosition="3" />
    <panel name="FullScreenMenuButton" />
    <panel name="ButtonBar" />
</screen>

<screen name="MovieSelectionSlim" position="fill" flags="wfNoBorder" backgroundColor="transparent">
    <panel name="MovieSelection" />
</screen>

<screen name="MovieListTags" position="fill" flags="wfNoBorder" backgroundColor="transparent">
    <panel name="FullScreenTemplate" />
    <panel name="FullScreenListWidget" />
</screen>

<screen name="MovieSelectionFileManagerList" position="fill" flags="wfNoBorder" title="">
    <panel name="FullScreenTemplate" />
    <panel name="FullScreenMenuButton" />
    <widget name="config" position="22,90" size="850,855" font="menulist;34" itemHeight="45" foregroundColor="maincolour" backgroundColor="menubackground" scrollbarMode="showOnDemand" enableWrapAround="1" zPosition="2"/>
    <widget name="description" position="1005,610" size="835,230" font="infobar2;32" foregroundColor="maincolour" backgroundColor="menubackground" transparent="1" valign="center" halign="center" zPosition="3" />
</screen>
```

**Key integration points:**

- **Line 15**: `<widget source="Service" render="CoverPixmap" ...>` - Displays cover artwork using the custom renderer
- **Lines 18-20**: Uses `FormatName` converter to transform folder paths into readable navigation text
- **Lines 24-26**: Uses `FormatDescription` converter to show rich category descriptions from db.json
- **Lines 30-32**: Uses `FormatExtra` converter for additional metadata filtering

Adjust positions and sizes to match your skin's layout.

## License

Copyright 2026 Pete Rai
Licensed under the Apache License, Version 2.0

See [LICENSE](LICENSE) file for details.

## Karmaware

This software is released with the [karmaware](https://pete-rai.github.io/karmaware) tag

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Links

- Forum discussion: [World of Satellite](https://world-of-satellite.com/threads/turning-enigma2-into-a-fully-browsable-vod-library.67535/)
- Repository: [https://github.com/pete-rai/enigma2-vod](https://github.com/pete-rai/enigma2-vod)

_– [Pete Rai](http://pete.rai.org.uk)_
