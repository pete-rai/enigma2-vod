# FormatDescription.py - Custom Enigma2 converter for formatting folder descriptions
#
# Copyright 2026 Pete Rai
# https://github.com/pete-rai/enigma2-vod
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Deploy to: /usr/lib/enigma2/python/Components/Converter/FormatDescription.py
#
# You may need to adjust permissions and ownership:
#   chmod 644 FormatDescription.py
#   chown root:root FormatDescription.py
#
# See project README for how to install into skin XML files.

from Components.Converter.Converter import Converter
from Components.Element import cached
import json

class FormatDescription(Converter):
    def __init__(self, type):
        Converter.__init__(self, type)

    @cached
    def getText(self):
        PREFIX  = "/media/hdd/movie"

        # Load REPLACE dictionary from db.json
        db_path = '/etc/xanadu/db.json'
        try:
            with open(db_path, 'r') as f:
                REPLACE = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, IOError):
            REPLACE = {}

        text = self.source.text or ""

        if text.startswith(PREFIX):
            text  = text.rstrip("/")
            parts = text.split("/")
            name  = parts[-1] or ""
            category = parts[-2] or ""


            if name == ".Trash":
                text = "Rummage in the deleted items bin."
            elif name == "Xanadu":
                text = "Welcome to the pleasure dome of classic cinema."
            elif category in REPLACE:
                if name in REPLACE[category]:
                    text = REPLACE[category][name]
            else:
                text = "Main PVR List."

        return text

    text = property(getText)
