"""Segment fixture data based on strava-api-v3.yaml."""

SUMMARY_SEGMENT = {
    "id": 229781,
    "resource_state": 2,
    "name": "Hawk Hill",
    "activity_type": "Ride",
    "distance": 2684.82,
    "average_grade": 5.7,
    "maximum_grade": 14.2,
    "elevation_high": 245.3,
    "elevation_low": 92.4,
    "start_latlng": [37.8331119, -122.4834356],
    "end_latlng": [37.8280722, -122.4981393],
    "climb_category": 1,
    "city": "San Francisco",
    "state": "CA",
    "country": "United States",
    "private": False,
    "hazardous": False,
    "starred": False
}

DETAILED_SEGMENT = {
    "id": 229781,
    "resource_state": 3,
    "name": "Hawk Hill",
    "activity_type": "Ride",
    "distance": 2684.82,
    "average_grade": 5.7,
    "maximum_grade": 14.2,
    "elevation_high": 245.3,
    "elevation_low": 92.4,
    "start_latlng": [37.8331119, -122.4834356],
    "end_latlng": [37.8280722, -122.4981393],
    "start_latitude": 37.8331119,
    "start_longitude": -122.4834356,
    "end_latitude": 37.8280722,
    "end_longitude": -122.4981393,
    "climb_category": 1,
    "city": "San Francisco",
    "state": "CA",
    "country": "United States",
    "private": False,
    "hazardous": False,
    "starred": False,
    "created_at": "2009-09-21T20:29:41.000Z",
    "updated_at": "2018-02-15T09:04:18.000Z",
    "total_elevation_gain": 155.733,
    "map": {
        "id": "s229781",
        "polyline": "}g|eFnpqjVl@En@Md@HbAd@...",
        "resource_state": 3
    },
    "effort_count": 309974,
    "athlete_count": 30623,
    "star_count": 2428,
    "athlete_segment_stats": {
        "pr_elapsed_time": 553,
        "pr_date": "1993-04-03T00:00:00.000Z",
        "effort_count": 2
    }
}

EXPLORE_SEGMENTS_RESPONSE = {
    "segments": [
        {
            "id": 229781,
            "resource_state": 2,
            "name": "Hawk Hill",
            "climb_category": 1,
            "climb_category_desc": "4",
            "avg_grade": 5.7,
            "start_latlng": [37.8331119, -122.4834356],
            "end_latlng": [37.8280722, -122.4981393],
            "elev_difference": 152.8,
            "distance": 2684.8,
            "points": "}g|eFnpqjVl@En@Md@...",
            "starred": False,
            "activity_type": "Ride"
        },
        {
            "id": 229782,
            "resource_state": 2,
            "name": "Panoramic Climb",
            "climb_category": 2,
            "climb_category_desc": "3",
            "avg_grade": 6.5,
            "start_latlng": [37.8400000, -122.4900000],
            "end_latlng": [37.8450000, -122.4950000],
            "elev_difference": 200.0,
            "distance": 3000.0,
            "points": "abcdefgh...",
            "starred": True,
            "activity_type": "Ride"
        }
    ]
}

SEGMENT_EFFORT = {
    "id": 1234556789,
    "resource_state": 3,
    "name": "Hawk Hill",
    "activity": {
        "id": 3454504,
        "resource_state": 1
    },
    "athlete": {
        "id": 54321,
        "resource_state": 1
    },
    "elapsed_time": 381,
    "moving_time": 340,
    "start_date": "2018-02-12T16:12:41.000Z",
    "start_date_local": "2018-02-12T08:12:41.000Z",
    "distance": 2684.82,
    "start_index": 65,
    "end_index": 83,
    "segment": {
        "id": 229781,
        "resource_state": 2,
        "name": "Hawk Hill",
        "activity_type": "Ride",
        "distance": 2684.82,
        "average_grade": 5.7,
        "maximum_grade": 14.2,
        "elevation_high": 245.3,
        "elevation_low": 92.4,
        "start_latlng": [37.8331119, -122.4834356],
        "end_latlng": [37.8280722, -122.4981393],
        "climb_category": 1,
        "city": "San Francisco",
        "state": "CA",
        "country": "United States",
        "private": False,
        "hazardous": False,
        "starred": False
    },
    "kom_rank": None,
    "pr_rank": 1,
    "achievements": [],
    "average_heartrate": 155.0,
    "max_heartrate": 175,
    "average_watts": 250.0,
    "device_watts": True,
    "average_cadence": 75.0
}

SEGMENT_EFFORTS_LIST = [
    {
        "id": 123456789,
        "resource_state": 2,
        "name": "Hawk Hill",
        "activity": {
            "id": 1234567890,
            "resource_state": 1
        },
        "athlete": {
            "id": 123445678689,
            "resource_state": 1
        },
        "elapsed_time": 1657,
        "moving_time": 1642,
        "start_date": "2007-09-15T08:15:29.000Z",
        "start_date_local": "2007-09-15T09:15:29.000Z",
        "distance": 6148.92,
        "start_index": 1102,
        "end_index": 1366,
        "device_watts": False,
        "average_watts": 220.2,
        "average_heartrate": 145.0,
        "pr_rank": 2
    }
]

SEGMENT_LEADERBOARD = {
    "entry_count": 5,
    "effort_count": 5,
    "kom_type": "kom",
    "entries": [
        {
            "athlete_name": "Jim W.",
            "elapsed_time": 291,
            "moving_time": 291,
            "start_date": "2018-12-01T12:00:00.000Z",
            "start_date_local": "2018-12-01T04:00:00.000Z",
            "rank": 1
        },
        {
            "athlete_name": "Chris D.",
            "elapsed_time": 295,
            "moving_time": 295,
            "start_date": "2018-11-15T14:30:00.000Z",
            "start_date_local": "2018-11-15T06:30:00.000Z",
            "rank": 2
        },
        {
            "athlete_name": "Sarah M.",
            "elapsed_time": 302,
            "moving_time": 300,
            "start_date": "2018-10-20T10:15:00.000Z",
            "start_date_local": "2018-10-20T02:15:00.000Z",
            "rank": 3
        },
        {
            "athlete_name": "Mike R.",
            "elapsed_time": 310,
            "moving_time": 308,
            "start_date": "2018-09-10T16:00:00.000Z",
            "start_date_local": "2018-09-10T08:00:00.000Z",
            "rank": 4
        },
        {
            "athlete_name": "Emily T.",
            "elapsed_time": 315,
            "moving_time": 312,
            "start_date": "2018-08-05T08:45:00.000Z",
            "start_date_local": "2018-08-05T00:45:00.000Z",
            "rank": 5
        }
    ]
}
