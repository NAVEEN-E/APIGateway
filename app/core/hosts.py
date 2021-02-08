from django.conf import settings
from django_hosts import (
    host,
    patterns,
)

if settings.USE_ENVVARS_FOR_HOST_ROUTING:
    host_patterns = patterns(
        '',
        host(settings.DEFAULT_HOST_PATTERN, 'admin.urls', name='itt-enphase-admin'),
        host(settings.INTERNAL_PORTAL_HOST_PATTERN, 'admin.urls_admin', name='admin'),
        host(settings.PORTAL_HOST_PATTERN, 'admin.urls_app', name='app'),
    )
else:
    host_patterns = patterns(
        '',
        host(
            r'itt-enphase-admin-server[.](dev|qa|platform)[.]linksvc[.]com',
            'admin.urls',
            name='itt-enphase-admin',
        ),
        host(r'admin([.](dev|qa))?[.]ittdigital[.]com', 'admin.urls_admin', name='admin'),
        host(r'app([.](dev|qa))?[.]ittdigital[.]com', 'admin.urls_app', name='app'),
        host(r'localhost(.*)', 'admin.urls', name='localhost'),
        host(r'admin.localhost(.*)', 'admin.urls_admin', name='localhost-admin'),
        host(r'app.local.ittdigital.com(.*)', 'admin.urls_app', name='local-app'),
    )
