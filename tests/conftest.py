import os

# The room, server and connector tests drive the demo engine; the real engine has its own tests
# (test_engine.py) with a fake site and a fake brain. Set before errand.server is imported, and
# passed on to the `errand start` the room tests launch.
os.environ.setdefault('ERRAND_DEMO', '1')
