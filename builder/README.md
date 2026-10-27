R9 guided Builder source. Tested on Windows with Python 3.13.3.

Install development requirements and run: python -m unittest discover -s builder -p "test_*.py"
The matching authenticated DATA is required for SDK setup and real builds.
Source mode expects DATA beside builder/app.py, or an explicit --data CLI argument.
No DATA, SDK binary, game-derived code, game/font/save or private shader payload is in this source branch.
The frozen EXE uses its adjacent matching DATA.
