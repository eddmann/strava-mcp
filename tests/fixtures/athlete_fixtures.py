"""Athlete fixture data based on strava-api-v3.yaml."""

DETAILED_ATHLETE = {
    "id": 1234567890987654400,
    "username": "marianne_t",
    "resource_state": 3,
    "firstname": "Marianne",
    "lastname": "Teutenberg",
    "city": "San Francisco",
    "state": "CA",
    "country": "US",
    "sex": "F",
    "premium": True,
    "summit": True,
    "created_at": "2017-11-14T02:30:05.000Z",
    "updated_at": "2018-02-06T19:32:20.000Z",
    "badge_type_id": 4,
    "profile_medium": "https://xxxxxx.cloudfront.net/pictures/athletes/123456789/123456789/2/medium.jpg",
    "profile": "https://xxxxx.cloudfront.net/pictures/athletes/123456789/123456789/2/large.jpg",
    "friend": None,
    "follower": None,
    "follower_count": 5,
    "friend_count": 5,
    "mutual_friend_count": 0,
    "athlete_type": 1,
    "date_preference": "%m/%d/%Y",
    "measurement_preference": "feet",
    "clubs": [],
    "ftp": None,
    "weight": 0,
    "bikes": [
        {
            "id": "b12345678987655",
            "primary": True,
            "name": "EMC",
            "resource_state": 2,
            "distance": 0
        }
    ],
    "shoes": [
        {
            "id": "g12345678987655",
            "primary": True,
            "name": "adidas",
            "resource_state": 2,
            "distance": 4904
        }
    ]
}

ATHLETE_STATS = {
    "biggest_ride_distance": 150000.0,
    "biggest_climb_elevation_gain": 2000.0,
    "recent_ride_totals": {
        "count": 5,
        "distance": 50000.0,
        "moving_time": 10000,
        "elapsed_time": 10500,
        "elevation_gain": 500.0,
        "achievement_count": 2
    },
    "recent_run_totals": {
        "count": 3,
        "distance": 15000.0,
        "moving_time": 3600,
        "elapsed_time": 3700,
        "elevation_gain": 100.0,
        "achievement_count": 1
    },
    "recent_swim_totals": {
        "count": 2,
        "distance": 2000.0,
        "moving_time": 1800,
        "elapsed_time": 1900,
        "elevation_gain": 0.0,
        "achievement_count": 0
    },
    "ytd_ride_totals": {
        "count": 50,
        "distance": 500000.0,
        "moving_time": 100000,
        "elapsed_time": 105000,
        "elevation_gain": 5000.0,
        "achievement_count": 20
    },
    "ytd_run_totals": {
        "count": 30,
        "distance": 150000.0,
        "moving_time": 36000,
        "elapsed_time": 37000,
        "elevation_gain": 1000.0,
        "achievement_count": 10
    },
    "ytd_swim_totals": {
        "count": 20,
        "distance": 20000.0,
        "moving_time": 18000,
        "elapsed_time": 19000,
        "elevation_gain": 0.0,
        "achievement_count": 5
    },
    "all_ride_totals": {
        "count": 500,
        "distance": 5000000.0,
        "moving_time": 1000000,
        "elapsed_time": 1050000,
        "elevation_gain": 50000.0,
        "achievement_count": 200
    },
    "all_run_totals": {
        "count": 300,
        "distance": 1500000.0,
        "moving_time": 360000,
        "elapsed_time": 370000,
        "elevation_gain": 10000.0,
        "achievement_count": 100
    },
    "all_swim_totals": {
        "count": 200,
        "distance": 200000.0,
        "moving_time": 180000,
        "elapsed_time": 190000,
        "elevation_gain": 0.0,
        "achievement_count": 50
    }
}

ATHLETE_ZONES = {
    "heart_rate": {
        "custom_zones": False,
        "zones": [
            {"min": 0, "max": 140},
            {"min": 140, "max": 160},
            {"min": 160, "max": 175},
            {"min": 175, "max": 190},
            {"min": 190, "max": -1}
        ]
    },
    "power": {
        "zones": [
            {"min": 0, "max": 150},
            {"min": 150, "max": 200},
            {"min": 200, "max": 250},
            {"min": 250, "max": 300},
            {"min": 300, "max": -1}
        ]
    }
}

ATHLETE_ZONES_HR_ONLY = {
    "heart_rate": {
        "custom_zones": True,
        "zones": [
            {"min": 0, "max": 135},
            {"min": 135, "max": 155},
            {"min": 155, "max": 170},
            {"min": 170, "max": 185},
            {"min": 185, "max": -1}
        ]
    },
    "power": None
}
