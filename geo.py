import random
import json
import logging
from datetime import datetime, timedelta

from core.file_system import AndroidFileSystem

class GeoEngine:
    def __init__(self, fs: AndroidFileSystem, logger: logging.Logger):
        self.fs = fs
        self.logger = logger
        self.base_work = (40.7488, -73.9854) # Empire State
        self.base_home = (40.6781, -73.9441) # Brooklyn
        
        # Dwell logic state
        self.dwelling = False
        self.dwell_until = None
        self.last_pos = self.base_home

    def _jitter(self, lat, lon, amount=0.0005):
        return lat + random.uniform(-amount, amount), lon + random.uniform(-amount, amount)

    def _interpolate(self, start, end, progress):
        lat = start[0] + (end[0] - start[0]) * progress
        lon = start[1] + (end[1] - start[1]) * progress
        return lat, lon

    def get_location_for_time(self, dt: datetime):
        """
        Returns lat/long with Commute and Stop-and-Go (Dwell) logic.
        """
        # Check Dwell State
        if self.dwelling:
            if dt < self.dwell_until:
                return self._jitter(self.last_pos[0], self.last_pos[1], 0.0001) # Tiny jitter
            else:
                self.dwelling = False

        # Random chance to start dwelling (Stop for coffee/traffic)
        if not self.dwelling and random.random() < 0.05:
            self.dwelling = True
            self.dwell_until = dt + timedelta(minutes=random.randint(15, 60))
            return self.last_pos

        hour = dt.hour
        minute = dt.minute
        is_weekend = dt.weekday() >= 5
        pos = self.base_home

        if is_weekend:
            if 12 <= hour <= 15:
                pos = (self.base_home[0] + 0.01, self.base_home[1] + 0.01) # Park
            else:
                pos = self.base_home
            pos = self._jitter(pos[0], pos[1], 0.002)
        else:
            if 8 <= hour < 9: # Morning Commute
                progress = minute / 60.0
                lat, lon = self._interpolate(self.base_home, self.base_work, progress)
                pos = self._jitter(lat, lon, 0.001)
            elif 17 <= hour < 18: # Evening Commute
                progress = minute / 60.0
                lat, lon = self._interpolate(self.base_work, self.base_home, progress)
                pos = self._jitter(lat, lon, 0.001)
            elif 9 <= hour < 17: # Work
                pos = self._jitter(self.base_work[0], self.base_work[1], 0.0005)
            else: # Home
                pos = self._jitter(self.base_home[0], self.base_home[1], 0.002)
        
        self.last_pos = pos
        return pos

    def generate_track_file(self, points: list):
        """Saves JSON and KML tracks."""
        path = self.fs.get_path("sdcard") / "Location"
        path.mkdir(parents=True, exist_ok=True)
        
        # JSON
        try:
            with open(path / "history.json", "w") as f:
                json.dump(points, f, indent=2)
        except OSError: pass

        # KML Export
        kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>User Location History</name>
    <Style id="path"><LineStyle><color>ff0000ff</color><width>4</width></LineStyle></Style>
    <Placemark>
      <name>Track</name>
      <styleUrl>#path</styleUrl>
      <LineString>
        <coordinates>
"""
        for p in points:
            kml_content += f"{p['longitude']},{p['latitude']},0 "
        
        kml_content += """
        </coordinates>
      </LineString>
    </Placemark>
  </Document>
</kml>"""

        try:
            with open(path / "history.kml", "w") as f:
                f.write(kml_content)
        except OSError: pass