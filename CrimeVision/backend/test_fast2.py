import main
try:
    print(main.api_me_stats_alias('haziq', 31.4697, 74.2818, 'Johar Town'))
except Exception as e:
    import traceback
    traceback.print_exc()
