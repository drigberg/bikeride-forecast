from get_and_send_forecasts import (
    calc_degrees_north_from_coords,
    calc_difference_between_vectors)


class TestMath:
    """
    Reminder: coords are (lat, lon), which correspond to (y, x)
    """
    def test_calc_degrees_north_from_coords_due_north(cls):
        assert calc_degrees_north_from_coords((0, 0), (-1, 0)) == 0

    def test_calc_degrees_north_from_coords_due_east(cls):
        assert calc_degrees_north_from_coords((0, 0), (0, -1)) == 90

    def test_calc_degrees_north_from_coords_due_south(cls):
        assert calc_degrees_north_from_coords((0, 0), (1, 0)) == 180

    def test_calc_degrees_north_from_coords_due_west(cls):
        assert calc_degrees_north_from_coords((52, 5), (52, 5.1)) == 270

    def test_calc_degrees_north_from_coords_northeast(cls):
        assert calc_degrees_north_from_coords((0, 0), (-5.196, -3)) == 30
        assert calc_degrees_north_from_coords((1, 1), (-1, -1)) == 45
        assert calc_degrees_north_from_coords((0, 0), (-3, -5.196)) == 60

    def test_calc_degrees_north_from_coords_southeast(cls):
        assert calc_degrees_north_from_coords((0, 0), (3, -5.196)) == 120
        assert calc_degrees_north_from_coords((0, 0), (5, -5)) == 135
        assert calc_degrees_north_from_coords((0, 0), (5.196, -3)) == 150

    def test_calc_degrees_north_from_coords_southwest(cls):
        assert calc_degrees_north_from_coords((10, 10), (15, 15)) == 225
        assert calc_degrees_north_from_coords((10, 10), (13, 15.196)) == 240

    def test_calc_degrees_north_from_coords_northwest(cls):
        assert calc_degrees_north_from_coords((0, 0), (-5, 5)) == 315

    def test_calc_difference_between_vectors(cls):
        assert calc_difference_between_vectors(90, 90) == 0
        assert calc_difference_between_vectors(90, 45) == 45
        assert calc_difference_between_vectors(90, 0) == 90
        assert calc_difference_between_vectors(45, 315) == 90
        assert calc_difference_between_vectors(180, 90) == 90
        assert calc_difference_between_vectors(270, 0) == 90
        assert calc_difference_between_vectors(90, 180) == 90
        assert calc_difference_between_vectors(90, 270) == 180
        assert calc_difference_between_vectors(0, 180) == 180
        assert calc_difference_between_vectors(3, 183) == 180
        assert calc_difference_between_vectors(357, 177) == 180
