#!/usr/bin/env python3
import sys

if '--worker' in sys.argv:
    from folio.engine import worker
    worker()
else:
    from folio.app import main
    main()
