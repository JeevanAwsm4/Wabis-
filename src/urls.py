import os

from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path,include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/webhooks/',include("api.v1.webhooks.urls"))
]

urlpatterns += static('/assets/', document_root=os.path.join(settings.BASE_DIR, 'assets'))

