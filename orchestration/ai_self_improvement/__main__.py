"""Allow `python -m orchestration.ai_self_improvement` invocation."""
import sys
from .cli import main

sys.exit(main())
