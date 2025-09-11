from django.urls import path
from .views_cleanup import reset_database_view

urlpatterns = [
    path('admin/reset-database/', reset_database_view, name='reset_database'),
]
