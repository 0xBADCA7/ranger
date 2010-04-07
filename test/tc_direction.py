# Copyright (C) 2009, 2010  Roman Zimbelmann <romanz@lavabit.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

if __name__ == '__main__': from __init__ import init; init()

import unittest
from ranger.ext.direction import Direction
from ranger.ext.openstruct import OpenStruct

class TestDirections(unittest.TestCase):
	def test_symmetry(self):
		d1 = Direction(right=4, down=7, relative=True)
		d2 = Direction(left=-4, up=-7, absolute=False)

		def subtest(d):
			self.assertEqual(4, d.right())
			self.assertEqual(7, d.down())
			self.assertEqual(-4, d.left())
			self.assertEqual(-7, d.up())
			self.assertEqual(True, d.relative())
			self.assertEqual(False, d.absolute())

			self.assertTrue(d.horizontal())
			self.assertTrue(d.vertical())

		subtest(d1)
		subtest(d2)

	def test_conflicts(self):
		d3 = Direction(right=5, left=2, up=3, down=6,
				absolute=True, relative=True)
		self.assertEqual(d3.right(), -d3.left())
		self.assertEqual(d3.left(), -d3.right())
		self.assertEqual(d3.up(), -d3.down())
		self.assertEqual(d3.down(), -d3.up())
		self.assertEqual(d3.absolute(), not d3.relative())
		self.assertEqual(d3.relative(), not d3.absolute())

	def test_copy(self):
		d = Direction(right=5)
		c = d.copy()
		self.assertEqual(c.right(), d.right())
		d['right'] += 3
		self.assertNotEqual(c.right(), d.right())
		c['right'] += 3
		self.assertEqual(c.right(), d.right())

		self.assertFalse(d.vertical())
		self.assertTrue(d.horizontal())

	def test_duck_typing(self):
		dct = dict(right=7, down=-3)
		self.assertEqual(-7, Direction.left(dct))
		self.assertEqual(3, Direction.up(dct))


if __name__ == '__main__':
	unittest.main()

