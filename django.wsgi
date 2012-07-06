import os
import sys
import site

[~vetext~]
projectpath = '[~projectdirectory~]'
projectapppath = '[~projectdirectory~][~projectname~]'
if projectpath not in sys.path:
    sys.path.append(projectpath)
if projectapppath not in sys.path:
    sys.path.append(projectapppath)
os.environ['DJANGO_SETTINGS_MODULE'] = '[~projectname~].settings'

import django.core.handlers.wsgi

application = django.core.handlers.wsgi.WSGIHandler()
