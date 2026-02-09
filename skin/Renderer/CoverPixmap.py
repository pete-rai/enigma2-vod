# CoverPixmap.py - Custom Enigma2 renderer for movie cover art
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
# Deploy to: /usr/lib/enigma2/python/Components/Renderer/CoverPixmap.py
#
# You may need to adjust permissions and ownership:
#   chmod 644 CoverPixmap.py
#   chown root:root CoverPixmap.py
#
# See project README for how to install into skin XML files.

from Components.Renderer.Renderer import Renderer
from enigma import ePixmap
import os
import re
import unicodedata

class CoverPixmap(Renderer):
	def __init__(self):
		Renderer.__init__(self)

	def normalize_title(self, title):
		"""
		Normalize a movie title to match the media folder naming convention.
		Examples:
		  "Mr. Smith Goes to Washington" -> "mr-smith-goes-to-washington"
		  "12 Angry Men" -> "12-angry-men"
		  "2001: A Space Odyssey" or "2001- A Space Odyssey" -> "2001-a-space-odyssey"
		  "It's a Wonderful Life" -> "its-a-wonderful-life"
		  "Avengers- Endgame" -> "avengers-endgame"
		  "Amélie" -> "amelie"
		"""

		# Remove accents/diacritical marks (é -> e, ñ -> n, etc.)
		normalized = unicodedata.normalize('NFKD', title)
		normalized = ''.join([c for c in normalized if not unicodedata.combining(c)])

		# Convert to lowercase
		normalized = normalized.lower()

		# Remove periods, colons, apostrophes, middle dot, and other special punctuation
		normalized = re.sub(r"[.,:;'?!\u00b7\u2022\u2027]", '', normalized)

		# Replace slashes and other separators with spaces
		normalized = re.sub(r'[/\\()\[\]]', ' ', normalized)

		# Replace multiple spaces with single space
		normalized = re.sub(r'\s+', ' ', normalized)

		# Trim and replace spaces with hyphens
		normalized = normalized.strip().replace(' ', '-')

		# Collapse multiple hyphens into single hyphen
		normalized = re.sub(r'-+', '-', normalized)

		return normalized

	GUI_WIDGET = ePixmap

	def postWidgetCreate(self, instance):
		self.changed((self.CHANGED_DEFAULT,))

	def changed(self, what):
		if self.instance:
			PREFIX = "/media/hdd/movie/Xanadu"
			COVER_BASE = "/etc/xanadu"
			FALLBACK = "/etc/xanadu/transparent.png"

			cover_path = FALLBACK

			# Get the service path from ServiceEvent source
			if self.source and hasattr(self.source, 'service') and self.source.service:
				text = self.source.service.getPath() or ""

				# Handle folders
				if text.startswith(PREFIX) and text.endswith('/'):
					# Extract the path after PREFIX
					# e.g., /media/hdd/movie/Xanadu/ -> "" (root xanadu)
					# e.g., /media/hdd/movie/Xanadu/Country/USA/ -> Country/USA
					relative_path = text[len(PREFIX):].lstrip('/').rstrip('/')

					# Check if we're at the root Xanadu folder
					if not relative_path:
						# /xanadu/ -> xanadu.png
						cover_path = os.path.join(COVER_BASE, "xanadu.png")
					else:
						# Get the folder parts
						parts = relative_path.split('/')

						if len(parts) == 1:
							# Category level: /xanadu/cast/ -> category/cast.png
							category_name = parts[0].lower()
							if category_name in ['cast', 'all', 'country', 'decade', 'director', 'duration', 'genre', 'theme']:
								cover_path = os.path.join(COVER_BASE, "category", category_name + ".png")
						elif len(parts) >= 2:
							# Item level: /xanadu/genre/western/ -> genre/western.png
							category = parts[0].lower().replace(' ', '_')
							folder = parts[1].lower().replace(' ', '_')

							# Special handling for Cast and Director - look in people folder
							if category in ['cast', 'director']:
								# Normalize person name: "Al Pacino" -> "al-pacino"
								person_name = parts[1].lower().replace(' ', '-')
								candidate = os.path.join(COVER_BASE, "people", person_name + ".png")
							else:
								# Build cover path for other categories
								candidate = os.path.join(COVER_BASE, category, folder + ".png")

							# Check if cover exists
							if os.path.isfile(candidate):
								cover_path = candidate
							elif category == "theme":
								# Try genre as fallback for theme
								genre_candidate = os.path.join(COVER_BASE, "genre", folder + ".png")
								if os.path.isfile(genre_candidate):
									cover_path = genre_candidate

				# Handle .ts files
				elif text.startswith(PREFIX) and text.endswith('.ts'):
					# Extract movie name from filename
					# e.g., /media/hdd/movie/Xanadu/Decade/1930s/19310101 0000 - Xanadu - City Lights.ts
					# e.g., 20020101 0000 - Xanadu - Catch Me If You Can.ts
					filename = os.path.basename(text)

					# Extract the date part to get the year
					date_match = re.match(r'(\d{4})\d{4}', filename)
					year = date_match.group(1) if date_match else None

					# Split by " - " and get the last part before .ts
					parts = filename.rsplit(' - ', 1)
					if len(parts) == 2:
						movie_name = parts[1].replace('.ts', '')
						# Use the mapper to normalize the title
						movie_slug = self.normalize_title(movie_name)

						# Try multiple variations to find the cover
						candidates = [
							os.path.join(COVER_BASE, "cover", movie_slug + ".png"),
						]

						# Add year suffix variants if we have a year
						if year:
							candidates.append(os.path.join(COVER_BASE, "cover", movie_slug + "-" + year + ".png"))

						# For some movies, try common year suffixes (1939-2024 range)
						# This handles cases where the folder has a year but the filename doesn't
						if not any(movie_slug.endswith(f"-{y}") for y in range(1900, 2030)):
							# Try adding the file's year
							if year:
								candidates.insert(1, os.path.join(COVER_BASE, "cover", movie_slug + "-" + year + ".png"))

						# Try each candidate
						for candidate in candidates:
							if os.path.isfile(candidate):
								cover_path = candidate
								break

			# Log only when image is not found (falls back to transparent)
			if cover_path == FALLBACK and self.source and hasattr(self.source, 'service') and self.source.service:
				try:
					with open("/tmp/coverpixmap_debug.log", "a") as f:
						f.write(f"\n=== IMAGE NOT FOUND ===\n")
						f.write(f"path={self.source.service.getPath()}\n")
						if hasattr(self.source.service, 'getName'):
							f.write(f"name={self.source.service.getName()}\n")
				except:
					pass

			if os.path.exists(cover_path):
				self.instance.setPixmapFromFile(cover_path)
				self.instance.show()
			else:
				self.instance.hide()
