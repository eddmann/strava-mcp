"""Activity fixture data based on strava-api-v3.yaml."""

SUMMARY_ACTIVITY = {
    "resource_state": 2,
    "athlete": {
        "id": 134815,
        "resource_state": 1
    },
    "name": "Happy Friday",
    "distance": 24931.4,
    "moving_time": 4500,
    "elapsed_time": 4500,
    "total_elevation_gain": 0,
    "type": "Ride",
    "sport_type": "Ride",
    "workout_type": None,
    "id": 154504250376823,
    "external_id": "garmin_push_12345678987654321",
    "upload_id": 987654321234567900000,
    "start_date": "2018-05-02T12:15:09.000Z",
    "start_date_local": "2018-05-02T05:15:09.000Z",
    "timezone": "(GMT-08:00) America/Los_Angeles",
    "utc_offset": -25200,
    "start_latlng": None,
    "end_latlng": None,
    "location_city": None,
    "location_state": None,
    "location_country": "United States",
    "start_latitude": None,
    "start_longitude": None,
    "achievement_count": 0,
    "kudos_count": 3,
    "comment_count": 1,
    "athlete_count": 1,
    "photo_count": 0,
    "map": {
        "id": "a12345678987654321",
        "summary_polyline": None,
        "resource_state": 2
    },
    "trainer": True,
    "commute": False,
    "manual": False,
    "private": False,
    "flagged": False,
    "gear_id": "b12345678987654321",
    "from_accepted_tag": False,
    "average_speed": 5.54,
    "max_speed": 11,
    "average_cadence": 67.1,
    "average_watts": 175.3,
    "weighted_average_watts": 210,
    "kilojoules": 788.7,
    "device_watts": True,
    "has_heartrate": True,
    "average_heartrate": 140.3,
    "max_heartrate": 178,
    "max_watts": 406,
    "pr_count": 0,
    "total_photo_count": 1,
    "has_kudoed": False,
    "suffer_score": 82
}

DETAILED_ACTIVITY = {
    "id": 12345678987654320,
    "resource_state": 3,
    "external_id": "garmin_push_12345678987654321",
    "upload_id": 98765432123456780,
    "athlete": {
        "id": 134815,
        "resource_state": 1
    },
    "name": "Happy Friday",
    "distance": 28099,
    "moving_time": 4207,
    "elapsed_time": 4410,
    "total_elevation_gain": 516,
    "type": "Ride",
    "sport_type": "Ride",
    "start_date": "2018-02-16T14:52:54.000Z",
    "start_date_local": "2018-02-16T06:52:54.000Z",
    "timezone": "(GMT-08:00) America/Los_Angeles",
    "utc_offset": -28800,
    "start_latlng": [37.83, -122.26],
    "end_latlng": [37.83, -122.26],
    "start_latitude": 37.83,
    "start_longitude": -122.26,
    "achievement_count": 0,
    "kudos_count": 19,
    "comment_count": 0,
    "athlete_count": 1,
    "photo_count": 0,
    "map": {
        "id": "a1410355832",
        "polyline": "ki{eFvqfiVqAWQIGEEKAY...",
        "resource_state": 3,
        "summary_polyline": "ki{eFvqfiVsBmA`Feh@..."
    },
    "trainer": False,
    "commute": False,
    "manual": False,
    "private": False,
    "flagged": False,
    "gear_id": "b12345678987654321",
    "from_accepted_tag": False,
    "average_speed": 6.679,
    "max_speed": 18.5,
    "average_cadence": 78.5,
    "average_temp": 4,
    "average_watts": 185.5,
    "weighted_average_watts": 230,
    "kilojoules": 780.5,
    "device_watts": True,
    "has_heartrate": False,
    "max_watts": 743,
    "elev_high": 446.6,
    "elev_low": 17.2,
    "pr_count": 0,
    "total_photo_count": 2,
    "has_kudoed": False,
    "workout_type": 10,
    "suffer_score": None,
    "description": "",
    "calories": 870.2,
    "segment_efforts": [],
    "splits_metric": [
        {
            "distance": 1001.5,
            "elapsed_time": 141,
            "elevation_difference": 4.4,
            "moving_time": 141,
            "split": 1,
            "average_speed": 7.1,
            "pace_zone": 0
        }
    ],
    "laps": [],
    "gear": {
        "id": "b12345678987654321",
        "primary": True,
        "name": "Tarmac",
        "resource_state": 2,
        "distance": 32547610
    },
    "partner_brand_tag": None,
    "photos": {
        "primary": None,
        "count": 2
    },
    "highlighted_kudosers": [],
    "device_name": "Garmin Edge 1030",
    "embed_token": "18e4615989b47dd4ff3dc711b0aa4502e4b311a9",
    "segment_leaderboard_opt_out": False,
    "leaderboard_opt_out": False
}

ACTIVITY_LAPS = [
    {
        "id": 12345678987654320,
        "resource_state": 2,
        "name": "Lap 1",
        "activity": {
            "id": 12345678987654320,
            "resource_state": 1
        },
        "athlete": {
            "id": 12345678987654320,
            "resource_state": 1
        },
        "elapsed_time": 1691,
        "moving_time": 1587,
        "start_date": "2018-02-08T14:13:37.000Z",
        "start_date_local": "2018-02-08T06:13:37.000Z",
        "distance": 8046.72,
        "start_index": 0,
        "end_index": 1590,
        "total_elevation_gain": 270,
        "average_speed": 4.76,
        "max_speed": 9.4,
        "average_cadence": 79,
        "device_watts": True,
        "average_watts": 228.2,
        "lap_index": 1,
        "split": 1
    },
    {
        "id": 12345678987654321,
        "resource_state": 2,
        "name": "Lap 2",
        "activity": {
            "id": 12345678987654320,
            "resource_state": 1
        },
        "athlete": {
            "id": 12345678987654320,
            "resource_state": 1
        },
        "elapsed_time": 1500,
        "moving_time": 1450,
        "start_date": "2018-02-08T14:41:48.000Z",
        "start_date_local": "2018-02-08T06:41:48.000Z",
        "distance": 7500.0,
        "start_index": 1590,
        "end_index": 3000,
        "total_elevation_gain": 200,
        "average_speed": 5.0,
        "max_speed": 10.0,
        "average_cadence": 80,
        "device_watts": True,
        "average_watts": 235.0,
        "lap_index": 2,
        "split": 2
    }
]

ACTIVITY_STREAMS = {
    "time": {
        "data": [0, 10, 20, 30, 40, 50],
        "series_type": "time",
        "original_size": 6,
        "resolution": "high"
    },
    "distance": {
        "data": [0.0, 50.0, 100.0, 150.0, 200.0, 250.0],
        "series_type": "distance",
        "original_size": 6,
        "resolution": "high"
    },
    "altitude": {
        "data": [10.0, 15.0, 20.0, 25.0, 22.0, 18.0],
        "series_type": "distance",
        "original_size": 6,
        "resolution": "high"
    },
    "velocity_smooth": {
        "data": [5.0, 5.2, 5.1, 4.9, 5.0, 5.3],
        "series_type": "distance",
        "original_size": 6,
        "resolution": "high"
    },
    "heartrate": {
        "data": [120, 125, 130, 135, 140, 145],
        "series_type": "distance",
        "original_size": 6,
        "resolution": "high"
    },
    "cadence": {
        "data": [70, 75, 80, 80, 75, 70],
        "series_type": "distance",
        "original_size": 6,
        "resolution": "high"
    },
    "watts": {
        "data": [150, 180, 200, 220, 210, 190],
        "series_type": "distance",
        "original_size": 6,
        "resolution": "high"
    }
}

ACTIVITY_ZONES = [
    {
        "type": "heartrate",
        "sensor_based": True,
        "custom_zones": False,
        "score": 82,
        "points": 100,
        "distribution_buckets": [
            {"min": 0, "max": 142, "time": 1200},
            {"min": 142, "max": 155, "time": 900},
            {"min": 155, "max": 162, "time": 600},
            {"min": 162, "max": 174, "time": 300},
            {"min": 174, "max": None, "time": 500}
        ]
    },
    {
        "type": "power",
        "sensor_based": True,
        "custom_zones": True,
        "score": 95,
        "points": 120,
        "distribution_buckets": [
            {"min": 0, "max": 143, "time": 800},
            {"min": 143, "max": 186, "time": 1000},
            {"min": 186, "max": 229, "time": 700},
            {"min": 229, "max": 286, "time": 400},
            {"min": 286, "max": 343, "time": 200},
            {"min": 343, "max": 999, "time": 100}
        ]
    }
]

ACTIVITY_COMMENTS = [
    {
        "id": 123456789,
        "activity_id": 12345678987654320,
        "text": "Great ride! Weather looked perfect.",
        "athlete": {
            "id": 987654,
            "resource_state": 2,
            "firstname": "John",
            "lastname": "Doe",
            "profile_medium": "https://example.com/avatar.jpg",
            "profile": "https://example.com/avatar.jpg",
            "city": "San Francisco",
            "state": "CA",
            "country": "United States",
            "sex": "M",
            "premium": True,
            "summit": True,
            "created_at": "2018-01-01T00:00:00.000Z",
            "updated_at": "2018-01-01T00:00:00.000Z"
        },
        "created_at": "2018-02-16T15:23:45.000Z"
    },
    {
        "id": 123456790,
        "activity_id": 12345678987654320,
        "text": "Nice work out there!",
        "athlete": {
            "id": 987655,
            "resource_state": 2,
            "firstname": "Jane",
            "lastname": "Smith",
            "profile_medium": "https://example.com/avatar2.jpg",
            "profile": "https://example.com/avatar2.jpg",
            "city": "Oakland",
            "state": "CA",
            "country": "United States",
            "sex": "F",
            "premium": False,
            "summit": False,
            "created_at": "2017-01-01T00:00:00.000Z",
            "updated_at": "2017-01-01T00:00:00.000Z"
        },
        "created_at": "2018-02-16T16:45:12.000Z"
    }
]

ACTIVITY_KUDOERS = [
    {
        "id": 111111,
        "resource_state": 2,
        "firstname": "Alice",
        "lastname": "Johnson",
        "profile_medium": "https://example.com/alice.jpg",
        "profile": "https://example.com/alice.jpg",
        "city": "Berkeley",
        "state": "CA",
        "country": "United States",
        "sex": "F",
        "premium": True,
        "summit": True,
        "created_at": "2016-01-01T00:00:00.000Z",
        "updated_at": "2016-01-01T00:00:00.000Z"
    },
    {
        "id": 222222,
        "resource_state": 2,
        "firstname": "Bob",
        "lastname": "Williams",
        "profile_medium": "https://example.com/bob.jpg",
        "profile": "https://example.com/bob.jpg",
        "city": "Palo Alto",
        "state": "CA",
        "country": "United States",
        "sex": "M",
        "premium": False,
        "summit": False,
        "created_at": "2015-01-01T00:00:00.000Z",
        "updated_at": "2015-01-01T00:00:00.000Z"
    },
    {
        "id": 333333,
        "resource_state": 2,
        "firstname": "Charlie",
        "lastname": "Brown",
        "profile_medium": "https://example.com/charlie.jpg",
        "profile": "https://example.com/charlie.jpg",
        "city": None,
        "state": None,
        "country": None,
        "sex": "M",
        "premium": True,
        "summit": True,
        "created_at": "2014-01-01T00:00:00.000Z",
        "updated_at": "2014-01-01T00:00:00.000Z"
    }
]
