"""Route fixture data based on strava-api-v3.yaml."""

ROUTE = {
    "id": 987654,
    "name": "Morning Commute",
    "description": "My daily ride to work",
    "athlete": {
        "id": 123456,
        "resource_state": 1
    },
    "distance": 15000.0,
    "elevation_gain": 150.0,
    "map": {
        "id": "r987654",
        "polyline": "abcdefgh...",
        "summary_polyline": "xyz123...",
        "resource_state": 3
    },
    "type": 1,
    "sub_type": 1,
    "private": False,
    "starred": True,
    "timestamp": 1618000000,
    "segments": [],
    "estimated_moving_time": 2400,
    "created_at": "2021-04-10T08:00:00.000Z",
    "updated_at": "2021-04-10T08:00:00.000Z",
    "id_str": "987654",
    "resource_state": 3
}

ROUTE_LIST = [
    {
        "id": 987654,
        "name": "Morning Commute",
        "description": "My daily ride to work",
        "athlete": {
            "id": 123456,
            "resource_state": 1
        },
        "distance": 15000.0,
        "elevation_gain": 150.0,
        "map": {
            "id": "r987654",
            "summary_polyline": "xyz123...",
            "resource_state": 2
        },
        "type": 1,
        "sub_type": 1,
        "private": False,
        "starred": True,
        "estimated_moving_time": 2400,
        "created_at": "2021-04-10T08:00:00.000Z",
        "resource_state": 2
    },
    {
        "id": 987655,
        "name": "Weekend Loop",
        "description": "Long weekend ride",
        "athlete": {
            "id": 123456,
            "resource_state": 1
        },
        "distance": 50000.0,
        "elevation_gain": 800.0,
        "map": {
            "id": "r987655",
            "summary_polyline": "abc456...",
            "resource_state": 2
        },
        "type": 1,
        "sub_type": 1,
        "private": True,
        "starred": False,
        "estimated_moving_time": 7200,
        "created_at": "2021-04-11T08:00:00.000Z",
        "resource_state": 2
    }
]

GPX_DATA = """<?xml version="1.0" encoding="UTF-8"?>
<gpx creator="Strava" version="1.1" xmlns="http://www.topografix.com/GPX/1/1">
  <metadata>
    <name>Morning Commute</name>
  </metadata>
  <trk>
    <name>Morning Commute</name>
    <trkseg>
      <trkpt lat="37.7749" lon="-122.4194">
        <ele>10.0</ele>
      </trkpt>
      <trkpt lat="37.7750" lon="-122.4195">
        <ele>11.0</ele>
      </trkpt>
    </trkseg>
  </trk>
</gpx>"""

TCX_DATA = """<?xml version="1.0" encoding="UTF-8"?>
<TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2">
  <Courses>
    <Course>
      <Name>Morning Commute</Name>
      <Lap>
        <TotalTimeSeconds>2400</TotalTimeSeconds>
        <DistanceMeters>15000.0</DistanceMeters>
      </Lap>
      <Track>
        <Trackpoint>
          <Position>
            <LatitudeDegrees>37.7749</LatitudeDegrees>
            <LongitudeDegrees>-122.4194</LongitudeDegrees>
          </Position>
          <AltitudeMeters>10.0</AltitudeMeters>
        </Trackpoint>
      </Track>
    </Course>
  </Courses>
</TrainingCenterDatabase>"""
