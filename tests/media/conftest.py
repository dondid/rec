# Reuse existing Debian Pillow only in this test process; never pip-install into audio.
import sys
sys.path.append('/usr/lib/python3/dist-packages')
