import sys
sys.path.append('.')
from main import api_me_stats_alias
try:
    res = api_me_stats_alias('test_user', 31.4697, 74.2818, 'Johar Town')
    print('Result:', res)
except Exception as e:
    import traceback
    traceback.print_exc()
