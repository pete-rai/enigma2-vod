# FormatExtra.py - Custom Enigma2 converter for extracting extra info from filenames
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
# Deploy to: /usr/lib/enigma2/python/Components/Converter/FormatExtra.py
#
# You may need to adjust permissions and ownership:
#   chmod 644 FormatExtra.py
#   chown root:root FormatExtra.py
#
# See project README for how to install into skin XML files.

from Components.Converter.Converter import Converter
from Components.Element import cached

class FormatExtra(Converter):
    def __init__(self, type):
        Converter.__init__(self, type)

    @cached
    def getText(self):
        PREFIX = "/media/hdd/movie"

        text  = self.source.text or ""
        parts = text.split("-")

        if text.startswith(PREFIX) or len(parts) < 3:
            text = ""

        return text

    text = property(getText)
