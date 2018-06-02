from sh_face_rec.videopipeline import VideoPipeline
import unittest
#Unit testing file

#execute: python -m unittest -v test.simpletest

class TestString(unittest.TestCase):
    def setUp(self):
        #is being called at beginning
        print("init test")

    def test_upper(self):
        self.assertEqual('foo'.upper(), 'FOO')
    
    def test_split(self):
        s='hello world'
        self.assertEqual(s.split(), ['hello','world'])

        with self.assertRaises(TypeError):
            s.split(2)

    def test_array(self):
        testimgnames = ['karsten', 'miriam', 'unknown', 'other']
        testimgarray = ['karsten', 'miriam', 'unknown', 'other']
        self.assertItemsEqual(testimgarray, testimgnames)


    def tearDown(self):
        #is being called at end
        print("clean up test")


if __name__ == '__main__':
    unittest.main()