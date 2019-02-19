from lib import calc_degrees_north_from_coords, calc_difference_between_vectors

class TestMath:
    def test_calc_degrees_north_from_coords(cls):
        assert calc_degrees_north_from_coords((0, 0), (0, 1)) == 0
        assert calc_degrees_north_from_coords((10, 10), (13, 15.196)) == 30
        assert calc_degrees_north_from_coords((10, 10), (15, 15)) == 45
        assert calc_degrees_north_from_coords((0, 0), (1, 0)) == 90
        assert calc_degrees_north_from_coords((0, 0), (5.196, -3)) == 120
        assert calc_degrees_north_from_coords((0, 0), (5, -5)) == 135
        assert calc_degrees_north_from_coords((0, 0), (3, -5.196)) == 150
        assert calc_degrees_north_from_coords((0, 0), (0, -1)) == 180
        assert calc_degrees_north_from_coords((0, 0), (-3, -5.196)) == 210
        assert calc_degrees_north_from_coords((1, 1), (-1, -1)) == 225
        assert calc_degrees_north_from_coords((0, 0), (-5.196, -3)) == 240
        assert calc_degrees_north_from_coords((0, 0), (-1, 0)) == 270
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
