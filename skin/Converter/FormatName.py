# FormatName.py - Custom Enigma2 converter for formatting folder/file names
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
# Deploy to: /usr/lib/enigma2/python/Components/Converter/FormatName.py
#
# You may need to adjust permissions and ownership:
#   chmod 644 FormatName.py
#   chown root:root FormatName.py
#
# See project README for how to install into skin XML files.

from Components.Converter.Converter import Converter
from Components.Element import cached

class FormatName(Converter):
    def __init__(self, type):
        Converter.__init__(self, type)

    @cached
    def getText(self):
        PREFIX  = "/media/hdd/movie"
        REPLACE = {
            ".Trash": "Deleted Items"
        }

        text = self.source.text or ""

        if text.startswith(PREFIX):
            text = text[len(PREFIX):]
            text = text.strip("/")
            text = text.replace("/", " - ")

            for old, new in REPLACE.items():
                text = text.replace(old, new)

            if text == "":
                text = "PVR Movie List"

        return text

    text = property(getText)
