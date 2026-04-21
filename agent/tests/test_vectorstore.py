import unittest
from agent.vectorstore import VectorStore

class TestVectorStore(unittest.TestCase):

    def setUp(self):
        self.vectorstore = VectorStore()

    def test_insert_vector(self):
        self.vectorstore.insert_vector('test_id', [1.0, 2.0, 3.0])
        self.assertIn('test_id', self.vectorstore.vectors)

    def test_retrieve_vector(self):
        self.vectorstore.insert_vector('test_id', [1.0, 2.0, 3.0])
        vector = self.vectorstore.retrieve_vector('test_id')
        self.assertEqual(vector, [1.0, 2.0, 3.0])

if __name__ == '__main__':
    unittest.main()