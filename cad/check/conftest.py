import os
import sys

# let the tests import cqmodel however pytest is started
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
