import debug_toolbar
from django.urls import path, include

urlpatterns = [
    path('', include('fruits.urls')),
    path('__debug__/', include(debug_toolbar.urls)),
]
