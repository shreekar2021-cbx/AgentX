"""Unit tests for Haversine distance and crop-relevant farmer matching."""

import math
import unittest
from uuid import UUID

from app.services.nearby_farmers import (
    FarmerLocation,
    FarmerMatchCandidate,
    NearbyFarmerMatcher,
    preferred_farmer_location,
)
from app.utils.geography import haversine_distance_km

REPORTER = UUID("11111111-1111-4111-8111-111111111111")
NEARBY = UUID("22222222-2222-4222-8222-222222222222")
OTHER = UUID("33333333-3333-4333-8333-333333333333")
CROP_A = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
CROP_B = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")


class HaversineTests(unittest.TestCase):
    def test_same_point_has_zero_distance(self):
        self.assertEqual(haversine_distance_km(17.385, 78.4867, 17.385, 78.4867), 0)

    def test_one_degree_longitude_at_equator(self):
        self.assertAlmostEqual(haversine_distance_km(0, 0, 0, 1), 111.195, delta=0.01)

    def test_antimeridian_uses_shortest_arc(self):
        self.assertAlmostEqual(haversine_distance_km(0, 179.5, 0, -179.5), 111.195, delta=0.01)

    def test_invalid_and_non_finite_coordinates_are_rejected(self):
        for point in ((91, 0), (0, -181), (math.nan, 0), (0, math.inf)):
            with self.subTest(point=point), self.assertRaises(ValueError):
                haversine_distance_km(*point, 0, 0)


class NearbyFarmerMatcherTests(unittest.TestCase):
    def setUp(self):
        self.origin = FarmerLocation(latitude=0, longitude=0, source="manual")
        self.candidates = [
            FarmerMatchCandidate(
                farmer_id=REPORTER,
                location=FarmerLocation(latitude=0, longitude=0.01),
                active_crop_ids={CROP_A},
            ),
            FarmerMatchCandidate(
                farmer_id=NEARBY,
                location=FarmerLocation(latitude=0, longitude=0.02, source="manual"),
                active_crop_ids={CROP_A, CROP_B},
            ),
            FarmerMatchCandidate(
                farmer_id=OTHER,
                location=FarmerLocation(latitude=0, longitude=0.03),
                active_crop_ids={CROP_B},
            ),
        ]

    def test_excludes_reporting_farmer_and_filters_by_relevant_crop(self):
        results = NearbyFarmerMatcher().match(
            reporting_farmer_id=REPORTER,
            reporting_location=self.origin,
            relevant_crop_ids={CROP_A},
            candidates=self.candidates,
        )

        self.assertEqual([item.farmer_id for item in results], [NEARBY])
        self.assertEqual(results[0].matched_crop_ids, [CROP_A])
        self.assertAlmostEqual(results[0].distance_km, 2.224, delta=0.02)

    def test_radius_can_be_configured(self):
        result = NearbyFarmerMatcher(radius_km=2).match(
            reporting_farmer_id=REPORTER,
            reporting_location=self.origin,
            relevant_crop_ids={CROP_A},
            candidates=self.candidates,
        )
        self.assertEqual(result, [])

    def test_duplicate_farmer_candidates_return_nearest_match_once(self):
        candidates = self.candidates + [
            FarmerMatchCandidate(
                farmer_id=NEARBY,
                location=FarmerLocation(latitude=0, longitude=0.01),
                active_crop_ids={CROP_B},
            )
        ]
        results = NearbyFarmerMatcher().match(
            reporting_farmer_id=REPORTER,
            reporting_location=self.origin,
            relevant_crop_ids={CROP_A, CROP_B},
            candidates=[candidates[0], candidates[1], candidates[3]],
        )
        self.assertEqual(len(results), 1)
        self.assertAlmostEqual(results[0].distance_km, 1.112, delta=0.02)
        self.assertEqual(set(results[0].matched_crop_ids), {CROP_A, CROP_B})

    def test_empty_crop_set_matches_nobody(self):
        results = NearbyFarmerMatcher().match(
            reporting_farmer_id=REPORTER,
            reporting_location=self.origin,
            relevant_crop_ids=set(),
            candidates=self.candidates,
        )
        self.assertEqual(results, [])

    def test_farm_location_precedes_profile_and_profile_is_fallback(self):
        profile = FarmerLocation(latitude=1, longitude=2, source="manual")
        farm = FarmerLocation(latitude=3, longitude=4, source="gps")
        self.assertEqual(preferred_farmer_location(farm, profile), farm)
        self.assertEqual(preferred_farmer_location(None, profile), profile)
        self.assertIsNone(preferred_farmer_location(None, None))


if __name__ == "__main__":
    unittest.main()
