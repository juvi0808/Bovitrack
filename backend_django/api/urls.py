from django.urls import path
from . import views  # Imports the views.py file from the same directory

# This list holds all the URL patterns for the 'api' app.
urlpatterns = [
    path('farms/', views.farm_list, name='farm-list'),
    path('farm/<int:farm_id>/', views.farm_detail, name='farm-detail'),

    path('farm/<int:farm_id>/locations/', views.location_list, name='location-list'),
    path('farm/<int:farm_id>/location/<int:location_id>/', views.location_detail, name='location-detail'),

    path('farm/<int:farm_id>/location/<int:location_id>/sublocations/', views.sublocation_list, name='sublocation-list'),
    path('farm/<int:farm_id>/sublocation/<int:sublocation_id>/', views.sublocation_detail, name='sublocation-detail'),

    path('farm/<int:farm_id>/purchases/', views.purchase_list, name='purchase-list'),
    
    path('farm/<int:farm_id>/sales/', views.sale_list, name='sale-list'),
    path('farm/<int:farm_id>/purchase/<int:purchase_id>/sale/add/', views.sale_create, name='sale-create'),
    
    path('farm/<int:farm_id>/weightings/', views.weighting_list, name='weighting-list'),
    path('farm/<int:farm_id>/purchase/<int:purchase_id>/weighting/add/', views.weighting_create, name='weighting-create'),
    
    path('farm/<int:farm_id>/sanitary/', views.sanitary_protocol_list, name='sanitary-protocol-list'),
    path('farm/<int:farm_id>/purchase/<int:purchase_id>/sanitary/add/', views.sanitary_protocol_create, name='sanitary-protocol-create'),
    
    path('farm/<int:farm_id>/location_log/', views.location_change_list, name='location-change-list'),
    path('farm/<int:farm_id>/purchase/<int:purchase_id>/location/add/', views.location_change_create, name='location-change-create'),
    
    path('farm/<int:farm_id>/diets/', views.diet_log_list, name='diet-log-list'),
    path('farm/<int:farm_id>/purchase/<int:purchase_id>/diet/add/', views.diet_log_create, name='diet-log-create'),
    
    path('farm/<int:farm_id>/deaths/', views.death_list, name='death-list'),
    path('farm/<int:farm_id>/purchase/<int:purchase_id>/death/add/', views.death_create, name='death-create'),

    path('farm/<int:farm_id>/animal/search/', views.animal_search, name='animal-search'),
    path('farm/<int:farm_id>/animal/<int:purchase_id>/', views.animal_master_record, name='animal-master-record'),

    path('farm/<int:farm_id>/lots/summary/', views.lots_summary, name='lots-summary'),
    path('farm/<int:farm_id>/lot/<str:lot_number>/', views.lot_detail_summary, name='lot-detail-summary'),

    path('farm/<int:farm_id>/stock/active_summary/', views.active_stock_summary, name='active-stock-summary'),

    path('farm/<int:farm_id>/location/<int:location_id>/bulk_assign_sublocation/', views.bulk_assign_sublocation, name='bulk-assign-sublocation'),
]