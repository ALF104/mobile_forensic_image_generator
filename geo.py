import random
import json
import logging
from datetime import datetime, timedelta
from typing import Tuple

from core.file_system import AndroidFileSystem

class GeoEngine:
    def __init__(self, fs: AndroidFileSystem, logger: logging.Logger):
        self.fs = fs
        self.logger = logger
        
        # Base Coordinates (NYC Area)
        self.home = (40.6781, -73.9441) # Brooklyn
        self.work = (40.7488, -73.9854) # Midtown
        
        # Improvement #8: Waypoints
        self.waypoints = {
            "coffee": (40.6925, -73.9910), # Cobble Hill Coffee
            "gym": (40.7410, -73.9935),    # Chelsea Gym
            "park": (40.6602, -73.9690),   # Prospect Park
            "grocery": (40.6850, -73.9780) # Supermarket
        }
        
        self.last_pos = self.home

    def _jitter(self, lat, lon, amount=0.0005):
        """Adds small random variance to coordinates."""
        return lat + random.uniform(-amount, amount), lon + random.uniform(-amount, amount)

    def _interpolate(self, start: Tuple[float, float], end: Tuple[float, float], progress: float):
        """Linearly interpolates between two points."""
        lat = start[0] + (end[0] - start[0]) * progress
        lon = start[1] + (end[1] - start[1]) * progress
        return lat, lon

    def get_location_for_time(self, dt: datetime):
        """
        Returns lat/long based on a realistic daily schedule with waypoints.
        """
        hour = dt.hour
        minute = dt.minute
        is_weekend = dt.weekday() >= 5
        
        target_pos = self.home
        
        if is_weekend:
            if 10 <= hour <= 12:
                target_pos = self.waypoints["coffee"]
            elif 13 <= hour <= 16:
                target_pos = self.waypoints["park"]
            elif 17 <= hour <= 18:
                target_pos = self.waypoints["grocery"]
            else:
                target_pos = self.home
        else:
            # Weekday Routine
            if 7 <= hour < 8: # Commute to Coffee
                progress = minute / 60.0
                target_pos = self._interpolate(self.home, self.waypoints["coffee"], progress)
            elif 8 <= hour < 9: # Coffee to Work
                progress = minute / 60.0
                target_pos = self._interpolate(self.waypoints["coffee"], self.work, progress)
            elif 9 <= hour < 17: # At Work
                target_pos = self.work
            elif 17 <= hour < 18: # Work to Gym
                progress = minute / 60.0
                target_pos = self._interpolate(self.work, self.waypoints["gym"], progress)
            elif 18 <= hour < 19: # Gym
                target_pos = self.waypoints["gym"]
            elif 19 <= hour < 20: # Gym to Home
                progress = minute / 60.0
                target_pos = self._interpolate(self.waypoints["gym"], self.home, progress)
            else:
                target_pos = self.home

        # Always add a little jitter so we aren't statis
        self.last_pos = self._jitter(target_pos[0], target_pos[1], 0.0015)
        return self.last_pos

    def generate_track_file(self, points: list):
        """Saves JSON and KML tracks."""
        path = self.fs.get_path("sdcard") / "Location"
        path.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(path / "history.json", "w") as f:
                json.dump(points, f, indent=2)
        except OSError: pass

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