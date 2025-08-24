from django.urls import path
from . import views  # Imports the views.py file from the same directory

# This list holds all the URL patterns for the 'api' app.
urlpatterns = [
    path('farms/', views.farm_list, name='farm-list'),
    path('farm/<int:farm_id>/', views.farm_detail, name='farm-detail'),
    path('farm/<int:farm_id>/locations/', views.location_list, name='location-list'),
    path('farm/<int:farm_id>/purchases/', views.purchase_list, name='purchase-list'),
    path('farm/<int:farm_id>/sales/', views.sale_list, name='sale-list'),
    path('farm/<int:farm_id>/purchase/<int:purchase_id>/sale/add/', views.sale_create, name='sale-create'),
]