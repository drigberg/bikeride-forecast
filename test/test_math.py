from lib import calc_degrees_north_from_coords, calc_difference_between_vectors

class TestMath:
    def test_calc_degrees_north_from_coords(cls):
        assert calc_degrees_north_from_coords((52, 5), (52, 5.1)) == 270
        assert calc_degrees_north_from_coords((10, 10), (13, 15.196)) == 300
        assert calc_degrees_north_from_coords((10, 10), (15, 15)) == 315
        assert calc_degrees_north_from_coords((0, 0), (1, 0)) == 0
        assert calc_degrees_north_from_coords((0, 0), (5.196, -3)) == 30
        assert calc_degrees_north_from_coords((0, 0), (5, -5)) == 45
        assert calc_degrees_north_from_coords((0, 0), (3, -5.196)) == 60
        assert calc_degrees_north_from_coords((0, 0), (0, -1)) == 90
        assert calc_degrees_north_from_coords((0, 0), (-3, -5.196)) == 120
        assert calc_degrees_north_from_coords((1, 1), (-1, -1)) == 135
        assert calc_degrees_north_from_coords((0, 0), (-5.196, -3)) == 150
        assert calc_degrees_north_from_coords((0, 0), (-1, 0)) == 180
        assert calc_degrees_north_from_coords((0, 0), (-5, 5)) == 225

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
