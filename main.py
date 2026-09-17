#!/usr/bin/env python3
import sys

if '--worker' in sys.argv:
    from folio.engine_v036 import worker
    worker()
else:
    from folio.app import main
    main()
