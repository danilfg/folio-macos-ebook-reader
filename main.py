#!/usr/bin/env python3
import sys

if '--worker' in sys.argv:
    from lexumi.engine_v036 import worker
    worker()
else:
    from lexumi.app import main
    main()
