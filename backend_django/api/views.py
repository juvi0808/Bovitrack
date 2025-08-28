from django.shortcuts import render
from rest_framework.decorators import api_view, parser_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.pagination import PageNumberPagination
# Make sure Q is imported here
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Count, Subquery, OuterRef, Q, F, FloatField, Case, When, Sum, IntegerField, Avg, Value, ExpressionWrapper
from django.db.models.functions import Coalesce, Cast, Now, NullIf, TruncDate

from .models import Farm, Location, Purchase, LocationChange, Sublocation, Weighting, DietLog, Sale, Death, SanitaryProtocol
from .serializers import (FarmSerializer, LocationSerializer, SublocationSerializer, 
                        PurchaseCreateSerializer, PurchaseListSerializer, WeightingSerializer, 
                        WeightingCreateSerializer, LocationChangeSerializer, DietLogSerializer, SanitaryProtocolSerializer, 
                        SanitaryProtocolCreateSerializer, SaleCreateSerializer, SaleSerializer, LocationChangeCreateSerializer, 
                        DietLogCreateSerializer, DeathSerializer, DeathCreateSerializer, LocationCreateUpdateSerializer, 
                        LocationSummarySerializer, AnimalSummarySerializer, SublocationCreateUpdateSerializer, AnimalMasterRecordSerializer,
                        LotSummarySerializer, ActiveStockResponseSerializer, BulkAssignSublocationSerializer, ActiveStockSummaryKpiSerializer,
                        FullFarmExportSerializer
                        )   # We will add more serializers here later
                      
from datetime import datetime, date, timedelta
import random
import io
import csv
import os
import bisect
from pathlib import Path
import calendar
import json


@api_view(['GET', 'POST'])
def farm_list(request):
    """
    API view to retrieve a list of all farms or create a new farm.
    - Handles GET requests to /api/farms/
    - Handles POST requests to /api/farms/
    """
    if request.method == 'GET':
        # This part remains exactly the same
        farms = Farm.objects.all().order_by('name')
        serializer = FarmSerializer(farms, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        # 1. Initialize the serializer with the incoming data from the request
        serializer = FarmSerializer(data=request.data)
        
        # 2. Validate the data.
        #    DRF automatically checks if 'name' is provided and if it's unique,
        #    based on our model definition.
        if serializer.is_valid():
            # 3. If validation passes, save the new object to the database.
            serializer.save()
            # 4. Return the data for the newly created farm with a 201 CREATED status.
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        # 5. If validation fails, return the errors with a 400 BAD REQUEST status.
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
def farm_detail(request, farm_id):
    """
    API view to retrieve, update, or delete a single farm.
    - Handles GET /api/farm/<id>/
    - Handles PUT /api/farm/<id>/ (for renaming)
    - Handles DELETE /api/farm/<id>/
    """
    # First, try to get the farm object from the database.
    # If it doesn't exist, DRF will automatically handle the 404 Not Found error.
    try:
        farm = Farm.objects.get(pk=farm_id)
    except Farm.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        # This handles retrieving the details of one farm.
        serializer = FarmSerializer(farm)
        return Response(serializer.data)

    elif request.method == 'PUT':
        # This handles the update (rename) operation.
        # We initialize the serializer with the farm we want to update,
        # and provide the new data from the request.
        serializer = FarmSerializer(farm, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        # This one line triggers the database's cascading delete.
        farm.delete()
        # Return a success message with a 204 NO CONTENT status.
        return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['GET', 'POST'])
def location_list(request, farm_id):
    """
    API view to retrieve a list of all locations for a farm or create a new one.
    - Handles GET /api/farm/<farm_id>/locations/
    - Handles POST /api/farm/<farm_id>/locations/
    """
    if not Farm.objects.filter(pk=farm_id).exists():
        return Response({"error": "Farm not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        location_kpis_data = location_list.get_kpis_for_locations(farm_id)
        locations = Location.objects.filter(farm_id=farm_id).prefetch_related('sublocations').order_by('name')
        
        context = {
            'location_kpis': location_kpis_data.get('location_kpis', {}),
            'sublocation_counts': location_kpis_data.get('sublocation_kpis', {}),
        }
        
        serializer = LocationSerializer(locations, many=True, context=context)
        return Response(serializer.data)

    elif request.method == 'POST':
        context = {'farm_id': farm_id}
        serializer = LocationCreateUpdateSerializer(data=request.data, context=context)
        if serializer.is_valid():
            new_location = serializer.save(farm_id=farm_id)
            response_serializer = LocationSerializer(new_location) # Use rich serializer for response
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Helper method attached to the view function for organization
def get_kpis_for_locations(farm_id):
    active_animals_qs = Purchase.objects.filter(
        farm_id=farm_id, sale__isnull=True, death__isnull=True
    ).annotate(
        current_location_id=Subquery(
            LocationChange.objects.filter(animal=OuterRef('pk')).order_by('-date', '-id').values('location_id')[:1]
        ),
        current_sublocation_id=Subquery(
            LocationChange.objects.filter(animal=OuterRef('pk')).order_by('-date', '-id').values('sublocation_id')[:1]
        ),
        last_weight=Subquery(
            Weighting.objects.filter(animal=OuterRef('pk')).order_by('-date', '-id').values('weight_kg')[:1]
        ),
        last_weight_date=Subquery(
            Weighting.objects.filter(animal=OuterRef('pk')).order_by('-date', '-id').values('date')[:1]
        )
    )
    today = date.today()
    location_kpis, sublocation_kpis = {}, {}
    for animal in active_animals_qs:
        loc_id, subloc_id = animal.current_location_id, animal.current_sublocation_id
        if loc_id and loc_id not in location_kpis:
            location_kpis[loc_id] = {'animal_count': 0, 'total_actual': 0.0, 'total_forecasted': 0.0}
        if subloc_id and subloc_id not in sublocation_kpis:
            sublocation_kpis[subloc_id] = {'animal_count': 0}
        last_w = animal.last_weight or animal.entry_weight
        last_w_date = animal.last_weight_date or animal.entry_date
        days_for_gmd = (last_w_date - animal.entry_date).days
        gain = last_w - animal.entry_weight
        gmd = (gain / days_for_gmd) if days_for_gmd > 0 else 0.0
        days_since_weigh = (today - last_w_date).days
        forecasted_w = last_w + (gmd * days_since_weigh)
        if loc_id:
            location_kpis[loc_id]['animal_count'] += 1
            location_kpis[loc_id]['total_actual'] += last_w
            location_kpis[loc_id]['total_forecasted'] += forecasted_w
        if subloc_id:
            sublocation_kpis[subloc_id]['animal_count'] += 1
    return {'location_kpis': location_kpis, 'sublocation_kpis': sublocation_kpis}

location_list.get_kpis_for_locations = get_kpis_for_locations

@api_view(['GET', 'PUT', 'DELETE'])
def location_detail(request, farm_id, location_id):
    """
    API view to retrieve a detailed summary, update, or delete a single location.
    - Handles GET /api/farm/<farm_id>/location/<location_id>/ (Summary)
    - Handles PUT /api/farm/<farm_id>/location/<location_id>/ (Update)
    - Handles DELETE /api/farm/<farm_id>/location/<location_id>/ (Delete)
    """
    try:
        location = Location.objects.get(pk=location_id, farm_id=farm_id)
    except Location.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        # --- Step 1: Find the primary keys of active animals whose LATEST location is this one. ---
        latest_locations = LocationChange.objects.filter(
            animal=OuterRef('pk')
        ).order_by('-date', '-id')

        animal_ids_in_location = Purchase.objects.filter(
            farm_id=farm_id,
            sale__isnull=True,
            death__isnull=True
        ).annotate(
            current_location_id=Subquery(latest_locations.values('location_id')[:1])
        ).filter(
            current_location_id=location_id
        ).values_list('pk', flat=True)

        # --- Step 2: Now, run the complex KPI query ONLY on those specific animal IDs. ---
        latest_weightings = Weighting.objects.filter(animal=OuterRef('pk')).order_by('-date', '-id')
        latest_diets = DietLog.objects.filter(animal=OuterRef('pk')).order_by('-date', '-id')

        # --- FINAL CORRECTED ANNOTATIONS ---
        # --- FIX: Use TruncDate for reliable date math ---
        current_date = TruncDate(Now())
        days_on_farm = ExpressionWrapper((current_date - F('entry_date')) / timedelta(days=1), output_field=FloatField())
        
        last_weighting_date_subq = Subquery(latest_weightings.values('date')[:1])
        last_weighting_date_or_entry = Coalesce(last_weighting_date_subq, F('entry_date'))
        
        days_for_gmd_expr = last_weighting_date_subq - F('entry_date')
        days_for_gmd = ExpressionWrapper(days_for_gmd_expr / timedelta(days=1), output_field=FloatField())
        
        # Use Coalesce to handle animals with no weightings yet
        last_weight_kg = Coalesce(Subquery(latest_weightings.values('weight_kg')[:1]), F('entry_weight'))
        total_gain = last_weight_kg - F('entry_weight')
        gmd = total_gain / NullIf(days_for_gmd, Value(0.0), output_field=FloatField())
        
        days_since_last_weight = ExpressionWrapper((current_date - last_weighting_date_or_entry) / timedelta(days=1), output_field=FloatField())
        forecasted_weight = last_weight_kg + (gmd * days_since_last_weight)
        
        animals_qs = Purchase.objects.filter(
            pk__in=list(animal_ids_in_location)
        ).annotate(
            # Annotate with all the fields required by AnimalSummarySerializer
            current_age_months=F('entry_age') + (days_on_farm / 30.44),
            last_weight_kg=last_weight_kg,
            average_daily_gain_kg=gmd,
            forecasted_current_weight_kg=forecasted_weight,
            current_diet_type=Subquery(latest_diets.values('diet_type')[:1]),
            days_on_farm_int=Cast(days_on_farm, IntegerField()),
            last_weighting_date=last_weighting_date_subq,
            current_diet_intake=Subquery(latest_diets.values('daily_intake_percentage')[:1]),
            current_location_id=Subquery(latest_locations.values('location_id')[:1]),
            current_sublocation_id=Subquery(latest_locations.values('sublocation_id')[:1])
            # The faulty sublocation_name subquery is correctly removed.
            # The serializer will handle the name lookup.
        )

        # --- Step 3: Assemble the final response object ---
        summary_data = {
            'location_details': location,
            'animals': animals_qs
        }

        kpi_data = location_list.get_kpis_for_locations(farm_id)
        kpi_context = {
            'location_kpis': kpi_data.get('location_kpis', {}),
            'sublocation_counts': kpi_data.get('sublocation_kpis', {}),
        }   
        serializer = LocationSummarySerializer(summary_data, context=kpi_context)
        return Response(serializer.data)

    elif request.method == 'PUT':
        context = {'farm_id': farm_id}
        serializer = LocationCreateUpdateSerializer(location, data=request.data, context=context)
        if serializer.is_valid():
            updated_location = serializer.save()
            response_serializer = LocationSerializer(updated_location)
            return Response(response_serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        location.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['GET', 'POST'])
def sublocation_list(request, farm_id, location_id):
    """
    API view to list sublocations for a specific location or create a new one.
    - Handles GET /api/farm/<farm_id>/location/<location_id>/sublocations/
    - Handles POST /api/farm/<farm_id>/location/<location_id>/sublocations/
    """
    # Security: Ensure parent location exists and belongs to the farm for both methods.
    if not Location.objects.filter(pk=location_id, farm_id=farm_id).exists():
        return Response({"error": "Parent location not found on this farm."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        # List all sublocations belonging to the specific parent location
        sublocations = Sublocation.objects.filter(
            parent_location_id=location_id
        ).order_by('name')
        serializer = SublocationSerializer(sublocations, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        # Create a new sublocation within the specific parent location
        context = {'location_id': location_id}
        serializer = SublocationCreateUpdateSerializer(data=request.data, context=context)
        if serializer.is_valid():
            new_sublocation = serializer.save(farm_id=farm_id, parent_location_id=location_id)
            response_serializer = SublocationSerializer(new_sublocation)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
def sublocation_detail(request, farm_id, sublocation_id):
    """
    API view to retrieve, update, or delete a single sublocation.
    """
    # Security: Ensure the sublocation exists and belongs to the specified farm.
    try:
        sublocation = Sublocation.objects.get(pk=sublocation_id, farm_id=farm_id)
    except Sublocation.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = SublocationSerializer(sublocation)
        return Response(serializer.data)

    elif request.method == 'PUT':
        context = {'location_id': sublocation.parent_location_id}
        serializer = SublocationCreateUpdateSerializer(sublocation, data=request.data, context=context)
        if serializer.is_valid():
            updated_sublocation = serializer.save()
            response_serializer = SublocationSerializer(updated_sublocation)
            return Response(response_serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        sublocation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(['GET'])
def purchase_list(request, farm_id):
    """
    API view to list all purchases for a farm (paginated).
    This view follows the same pattern as other list views like sale_list.
    Handles GET /api/farm/<farm_id>/purchases/
    """
    if not Farm.objects.filter(pk=farm_id).exists():
        return Response({"error": "Farm not found."}, status=status.HTTP_404_NOT_FOUND)

    paginator = PageNumberPagination()
    paginator.page_size = 100

    purchases_qs = Purchase.objects.filter(farm_id=farm_id).order_by('-entry_date')

    paginated_purchases = paginator.paginate_queryset(purchases_qs, request)
    serializer = PurchaseListSerializer(paginated_purchases, many=True)
    
    return paginator.get_paginated_response(serializer.data)


# ADD THIS NEW FUNCTION FOR POST REQUESTS
@api_view(['POST'])
def purchase_create(request, farm_id):
    """
    API view to create a new purchase and its related initial records.
    Handles POST /api/farm/<farm_id>/purchases/add/
    """
    if not Farm.objects.filter(pk=farm_id).exists():
        return Response({"error": "Farm not found."}, status=status.HTTP_404_NOT_FOUND)
        
    context = {'farm_id': farm_id}
    serializer = PurchaseCreateSerializer(data=request.data, context=context)

    if serializer.is_valid():
        validated_data = serializer.validated_data
        
        location_id = validated_data.pop('location_id')
        initial_diet_type = validated_data.pop('initial_diet_type', None)
        daily_intake_percentage = validated_data.pop('daily_intake_percentage', None)
        protocols_data = validated_data.pop('sanitary_protocols', [])

        try:
            with transaction.atomic():
                new_purchase = Purchase.objects.create(farm_id=farm_id, **validated_data)
                Weighting.objects.create(
                    farm_id=farm_id, animal=new_purchase,
                    date=new_purchase.entry_date, weight_kg=new_purchase.entry_weight
                )
                LocationChange.objects.create(
                    farm_id=farm_id, animal=new_purchase,
                    date=new_purchase.entry_date, location_id=location_id
                )
                if initial_diet_type:
                    DietLog.objects.create(
                        farm_id=farm_id, animal=new_purchase, date=new_purchase.entry_date,
                        diet_type=initial_diet_type, daily_intake_percentage=daily_intake_percentage
                    )
                for protocol_data in protocols_data:
                    SanitaryProtocol.objects.create(farm_id=farm_id, animal=new_purchase, **protocol_data)
            
            response_serializer = PurchaseListSerializer(new_purchase)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {"error": f"An unexpected error occurred during save: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def sale_list(request, farm_id):
    """
    API view to list all sales for a specific farm.
    This view is now optimized with annotations and is paginated.
    """
    print(">>>> EXECUTING THE CORRECT sale_list VIEW <<<<")
    paginator = PageNumberPagination()
    paginator.page_size = 100

    # --- OPTIMIZATION: Subquery to get the final weight in the main query ---
    exit_weight_subquery = Subquery(
        Weighting.objects.filter(
            animal=OuterRef('animal'),
            date=OuterRef('date')
        ).values('weight_kg')[:1]
    )

    base_sales_qs = Sale.objects.filter(farm_id=farm_id).select_related('animal')

    # --- OPTIMIZATION: Annotate with all calculated fields at the database level ---
    annotated_sales = base_sales_qs.annotate(
        exit_weight_kg=exit_weight_subquery,
        days_on_farm_expr=(F('date') - F('animal__entry_date')),
        total_gain_expr=(F('exit_weight_kg') - F('animal__entry_weight'))
    ).annotate(
        days_on_farm=ExpressionWrapper(F('days_on_farm_expr') / timedelta(days=1), output_field=FloatField()),
        gmd_kg_day=Case(
            When(days_on_farm_expr__gt=timedelta(0), then=F('total_gain_expr') / F('days_on_farm')),
            default=0.0,
            output_field=FloatField()
        ),
        exit_age_months=F('animal__entry_age') + (F('days_on_farm') / 30.44)
    ).order_by('-date')

    paginated_sales = paginator.paginate_queryset(annotated_sales, request)
    serializer = SaleSerializer(paginated_sales, many=True)
    return paginator.get_paginated_response(serializer.data)

@api_view(['POST'])
def sale_create(request, farm_id, purchase_id):
    """
    API view to create a new Sale for a specific Purchase (animal).
    This also creates the final Weighting record for the animal.
    Handles POST /api/farm/<farm_id>/purchase/<purchase_id>/sale/
    """
    # --- Validation and Security ---
    try:
        # Ensure the animal exists and belongs to the correct farm.
        animal = Purchase.objects.get(pk=purchase_id, farm_id=farm_id)
    except Purchase.DoesNotExist:
        return Response({"error": "Animal not found on this farm."}, status=status.HTTP_404_NOT_FOUND)

    # Business Logic: Check if the animal has already been sold or recorded as dead.
    if hasattr(animal, 'sale'):
        return Response({"error": "This animal has already been sold."}, status=status.HTTP_409_CONFLICT)
    if hasattr(animal, 'death'):
        return Response({"error": "Cannot sell an animal that has been recorded as dead."}, status=status.HTTP_409_CONFLICT)

    # --- Data Processing ---
    serializer = SaleCreateSerializer(data=request.data)
    if serializer.is_valid():
        validated_data = serializer.validated_data
        exit_weight = validated_data.pop('exit_weight') # Get the extra field

        try:
            with transaction.atomic():
                # 1. Create the final Weighting record.
                final_weighting = Weighting.objects.create(
                    animal=animal,
                    farm_id=farm_id,
                    date=validated_data['date'],
                    weight_kg=exit_weight
                )

                # 2. Create the Sale record itself.
                # The validated_data dictionary now only contains 'date' and 'sale_price'.
                new_sale = Sale.objects.create(
                    animal=animal,
                    farm_id=farm_id,
                    **validated_data
                )
            
            # Use the detailed SaleSerializer for the response
            response_serializer = SaleSerializer(new_sale)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": f"An error occurred during save: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    # If the serializer is not valid, return the validation errors.
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def weighting_list(request, farm_id):
    """
    API view to list all weighting records for a specific farm.
    Now paginated for performance.
    """
    paginator = PageNumberPagination()
    paginator.page_size = 100

    weightings_qs = Weighting.objects.filter(farm_id=farm_id).select_related('animal').order_by('-date')
    
    paginated_weightings = paginator.paginate_queryset(weightings_qs, request)
    serializer = WeightingSerializer(paginated_weightings, many=True)
    return paginator.get_paginated_response(serializer.data)

@api_view(['POST'])
def weighting_create(request, farm_id, purchase_id):
    """
    API view to add a new weight record to a specific, existing animal.
    Handles POST /api/farm/<farm_id>/purchase/<purchase_id>/weighting/add/
    """
    # --- Validation and Security ---
    try:
        # Ensure the animal exists and belongs to the correct farm.
        animal = Purchase.objects.get(pk=purchase_id, farm_id=farm_id)
    except Purchase.DoesNotExist:
        return Response({"error": "Animal not found on this farm."}, status=status.HTTP_404_NOT_FOUND)

    # --- Data Processing ---
    serializer = WeightingCreateSerializer(data=request.data)
    if serializer.is_valid():
        # If validation is successful, create the new Weighting instance.
        # The 'animal' and 'farm' are associated here, not from the request body.
        new_weighting = serializer.save(animal=animal, farm_id=farm_id)

        # Use the detailed WeightingSerializer for the response to include
        # the animal's ear_tag and lot, matching the Flask API pattern.
        response_serializer = WeightingSerializer(new_weighting)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    # If the serializer is not valid, return the validation errors.
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def sanitary_protocol_list(request, farm_id):
    """
    API view to list all sanitary protocol events for a specific farm.
    Now paginated for performance.
    """
    paginator = PageNumberPagination()
    paginator.page_size = 100

    protocols_qs = SanitaryProtocol.objects.filter(
        farm_id=farm_id
    ).select_related('animal').order_by('-date')
    
    paginated_protocols = paginator.paginate_queryset(protocols_qs, request)
    serializer = SanitaryProtocolSerializer(paginated_protocols, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(['POST'])
def sanitary_protocol_create(request, farm_id, purchase_id):
    """
    Adds a batch of new sanitary protocol records to a specific animal.
    Also handles an optional, concurrent weight record.
    Handles POST /api/farm/<farm_id>/purchase/<purchase_id>/sanitary/add
    """
    # --- Validation and Security ---
    try:
        animal = Purchase.objects.get(pk=purchase_id, farm_id=farm_id)
    except Purchase.DoesNotExist:
        return Response({"error": "Animal not found on this farm."}, status=status.HTTP_404_NOT_FOUND)

    # --- Data Extraction and Validation ---
    protocols_data = request.data.get('protocols')
    optional_weight = request.data.get('weight_kg')

    if not isinstance(protocols_data, list):
        return Response({"error": "Request body must contain a 'protocols' list."}, status=status.HTTP_400_BAD_REQUEST)
    
    if not protocols_data:
         return Response({'error': "Protocols list cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)

    # Validate every protocol object in the list
    serializer = SanitaryProtocolCreateSerializer(data=protocols_data, many=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        with transaction.atomic():
            # 1. Create the optional Weighting record if provided.
            # Use the date from the first protocol as the reference date.
            if optional_weight and float(optional_weight) > 0:
                event_date = serializer.validated_data[0]['date']
                Weighting.objects.create(
                    animal=animal,
                    farm_id=farm_id,
                    date=event_date,
                    weight_kg=float(optional_weight)
                )

            # 2. Loop through the validated data and create all protocols.
            for protocol_data in serializer.validated_data:
                SanitaryProtocol.objects.create(
                    animal=animal,
                    farm_id=farm_id,
                    **protocol_data
                )
        
        return Response(
            {"message": f'{len(protocols_data)} protocols recorded successfully!'},
            status=status.HTTP_201_CREATED
        )

    except (ValueError, TypeError):
         return Response({"error": "Invalid 'weight_kg' format."}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({"error": f"An error occurred during save: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def location_change_list(request, farm_id):
    """
    API view to list all location change events for a specific farm.
    Now paginated for performance.
    """
    paginator = PageNumberPagination()
    paginator.page_size = 100

    changes_qs = LocationChange.objects.filter(
        farm_id=farm_id
    ).select_related('animal', 'location', 'sublocation').order_by('-date')
    
    paginated_changes = paginator.paginate_queryset(changes_qs, request)
    serializer = LocationChangeSerializer(paginated_changes, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(['POST'])
def location_change_create(request, farm_id, purchase_id):
    """
    Adds a new location change record to a specific animal,
    with optional sublocation and optional concurrent weighting.
    Handles POST /api/farm/<farm_id>/purchase/<purchase_id>/location/add/
    """
    # --- Validation and Security ---
    try:
        animal = Purchase.objects.get(pk=purchase_id, farm_id=farm_id)
    except Purchase.DoesNotExist:
        return Response({"error": "Animal not found on this farm."}, status=status.HTTP_404_NOT_FOUND)

    # --- Data Processing ---
    # Pass farm_id to the serializer's context for use in our custom validation.
    context = {'farm_id': farm_id}
    serializer = LocationChangeCreateSerializer(data=request.data, context=context)
    if serializer.is_valid():
        validated_data = serializer.validated_data
        optional_weight = validated_data.pop('weight_kg', None)

        try:
            with transaction.atomic():
                # 1. Create the LocationChange record.
                # The validated_data now perfectly matches the model's needs.
                new_change = LocationChange.objects.create(
                    animal=animal,
                    farm_id=farm_id,
                    **validated_data
                )

                # 2. Create the optional Weighting record.
                if optional_weight and float(optional_weight) > 0:
                    Weighting.objects.create(
                        animal=animal,
                        farm_id=farm_id,
                        date=new_change.date,
                        weight_kg=optional_weight
                    )
            
            # Use the "read" serializer for a rich response
            response_serializer = LocationChangeSerializer(new_change)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except (ValueError, TypeError):
             return Response({"error": "Invalid 'weight_kg' format."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"An error occurred during save: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def diet_log_list(request, farm_id):
    """
    API view to list all diet log events for a specific farm.
    Now paginated for performance.
    """
    paginator = PageNumberPagination()
    paginator.page_size = 100

    diets_qs = DietLog.objects.filter(
        farm_id=farm_id
    ).select_related('animal').order_by('-date')
    
    paginated_diets = paginator.paginate_queryset(diets_qs, request)
    serializer = DietLogSerializer(paginated_diets, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(['POST'])
def diet_log_create(request, farm_id, purchase_id):
    """
    Adds a new diet log record to a specific animal,
    with an optional concurrent weighting.
    Handles POST /api/farm/<farm_id>/purchase/<purchase_id>/diet/add/
    """
    # --- Validation and Security ---
    try:
        animal = Purchase.objects.get(pk=purchase_id, farm_id=farm_id)
    except Purchase.DoesNotExist:
        return Response({"error": "Animal not found on this farm."}, status=status.HTTP_404_NOT_FOUND)

    # --- Data Processing ---
    serializer = DietLogCreateSerializer(data=request.data)
    if serializer.is_valid():
        validated_data = serializer.validated_data
        optional_weight = validated_data.pop('weight_kg', None)

        try:
            with transaction.atomic():
                # 1. Create the DietLog record.
                new_diet_log = DietLog.objects.create(
                    animal=animal,
                    farm_id=farm_id,
                    **validated_data
                )

                # 2. Create the optional Weighting record.
                if optional_weight and float(optional_weight) > 0:
                    Weighting.objects.create(
                        animal=animal,
                        farm_id=farm_id,
                        date=new_diet_log.date,
                        weight_kg=optional_weight
                    )
            
            # Use the "read" serializer for the response
            response_serializer = DietLogSerializer(new_diet_log)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except (ValueError, TypeError):
             return Response({"error": "Invalid 'weight_kg' format."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"An error occurred during save: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def death_list(request, farm_id):
    """
    API view to list all death records for a specific farm.
    Handles GET /api/farm/<farm_id>/deaths/
    """
    print(">>>> EXECUTING THE CORRECT death_list VIEW <<<<")
    if not Farm.objects.filter(pk=farm_id).exists():
        return Response({"error": "Farm not found."}, status=status.HTTP_404_NOT_FOUND)

    paginator = PageNumberPagination()
    paginator.page_size = 100

    deaths_qs = Death.objects.filter(
        farm_id=farm_id
    ).select_related('animal').order_by('-date')
    
    paginated_deaths = paginator.paginate_queryset(deaths_qs, request)
    serializer = DeathSerializer(paginated_deaths, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(['POST'])
def death_create(request, farm_id, purchase_id):
    """
    Creates a new death record for a specific animal.
    Handles POST /api/farm/<farm_id>/purchase/<purchase_id>/death/add/
    """
    # --- Validation and Security ---
    try:
        animal = Purchase.objects.get(pk=purchase_id, farm_id=farm_id)
    except Purchase.DoesNotExist:
        return Response({"error": "Animal not found on this farm."}, status=status.HTTP_404_NOT_FOUND)

    # --- Business Logic Checks ---
    if hasattr(animal, 'sale'):
        return Response({"error": "Cannot record death. This animal has already been sold."}, status=status.HTTP_409_CONFLICT)
    if hasattr(animal, 'death'):
        return Response({"error": "A death record for this animal already exists."}, status=status.HTTP_409_CONFLICT)

    # --- Data Processing ---
    serializer = DeathCreateSerializer(data=request.data)
    if serializer.is_valid():
        new_death = serializer.save(animal=animal, farm_id=farm_id)
        
        # Use the "read" serializer for the response
        response_serializer = DeathSerializer(new_death)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)   

@api_view(['GET'])
def animal_search(request, farm_id):
    """
    Searches for active animals within a farm by their ear tag.
    Handles GET /api/farm/<farm_id>/animal/search?eartag=<value>
    """
    tag_to_search_raw = request.query_params.get('eartag')
    if not tag_to_search_raw:
        return Response({'error': 'An eartag parameter is required.'}, status=status.HTTP_400_BAD_REQUEST)

    tag_to_search = tag_to_search_raw.strip().strip('\'"')

    base_query = Purchase.objects.filter(
        farm_id=farm_id,
        ear_tag=tag_to_search,
        sale__isnull=True,
        death__isnull=True
    )

    # --- ENHANCED ANNOTATIONS ---
    # We now add annotations for every KPI field needed by the serializer.
    latest_weightings = Weighting.objects.filter(animal=OuterRef('pk')).order_by('-date', '-id')
    latest_diets = DietLog.objects.filter(animal=OuterRef('pk')).order_by('-date', '-id')
    latest_locations = LocationChange.objects.filter(animal=OuterRef('pk')).order_by('-date', '-id')

    days_on_farm_expr = (Now() - F('entry_date'))
    days_for_gmd_expr = (Subquery(latest_weightings.values('date')[:1]) - F('entry_date'))
    days_on_farm = Cast(days_on_farm_expr, FloatField()) / (24 * 60 * 60)
    days_for_gmd = Cast(days_for_gmd_expr, FloatField()) / (24 * 60 * 60)
    last_weight_kg = Subquery(latest_weightings.values('weight_kg')[:1])
    total_gain = last_weight_kg - F('entry_weight')
    gmd = total_gain / NullIf(days_for_gmd, 0.0)

    annotated_query = base_query.annotate(
        # Existing KPIs
        current_age_months=F('entry_age') + (days_on_farm / 30.44),
        last_weight_kg=last_weight_kg,
        average_daily_gain_kg=gmd,
        forecasted_current_weight_kg=last_weight_kg + (gmd * days_on_farm),
        current_diet_type=Subquery(latest_diets.values('diet_type')[:1]),
        
        # <-- NEWLY ADDED ANNOTATIONS -->
        days_on_farm_int=Cast(days_on_farm, IntegerField()),
        last_weighting_date=Subquery(latest_weightings.values('date')[:1]),
        current_diet_intake=Subquery(latest_diets.values('daily_intake_percentage')[:1]),
        current_location_id=Subquery(latest_locations.values('location_id')[:1]),
        current_location_name=Subquery(
            Location.objects.filter(pk=Subquery(latest_locations.values('location_id')[:1])).values('name')[:1]
        ),
        current_sublocation_id=Subquery(latest_locations.values('sublocation_id')[:1]),
        current_sublocation_name=Subquery(
            Sublocation.objects.filter(pk=Subquery(latest_locations.values('sublocation_id')[:1])).values('name')[:1]
        )
    )

    serializer = AnimalSummarySerializer(annotated_query, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def animal_master_record(request, farm_id, purchase_id):
    """
    Retrieves the complete master record for a single animal, including its
    purchase details, all historical events, and calculated KPIs.
    Handles GET /api/farm/<farm_id>/animal/<purchase_id>/
    """
    try:
        # This is the "Smart Hydration" fetch. We get the main object and all
        # of its related history in a single, optimized database hit.
        # - select_related: for one-to-one relations (sale, death)
        # - prefetch_related: for many-to-one relations (all history logs)
        animal = Purchase.objects.select_related(
            'sale', 'death'
        ).prefetch_related(
            'weightings',
            'protocols',
            'location_changes__location',
            'location_changes__sublocation',
            'diet_logs'
        ).get(pk=purchase_id, farm_id=farm_id)
    except Purchase.DoesNotExist:
        return Response(
            {"error": "This animal does not belong to the specified farm."},
            status=status.HTTP_404_NOT_FOUND
        )

    # The single, hydrated 'animal' object is passed to the serializer.
    # The serializer now handles all the complex logic of assembling the response.
    serializer = AnimalMasterRecordSerializer(animal)
    return Response(serializer.data)

@api_view(['GET'])
def lots_summary(request, farm_id):
    """
    Gets a summary of all active lots for a farm, with aggregated KPIs
    calculated efficiently in the database.
    Handles GET /api/farm/<farm_id>/lots/summary/
    """
    # --- Step 1: Security and Validation ---
    if not Farm.objects.filter(pk=farm_id).exists():
        return Response({"error": "Farm not found."}, status=status.HTTP_404_NOT_FOUND)

    # --- Step 2: Define Reusable KPI Expressions for a Single Animal ---
    latest_weightings = Weighting.objects.filter(animal=OuterRef('pk')).order_by('-date', '-id')

    # --- FINAL CORRECTED ANNOTATIONS ---
    # --- FIX: Use TruncDate for reliable date math ---
    current_date = TruncDate(Now())
    days_on_farm = ExpressionWrapper((current_date - F('entry_date')) / timedelta(days=1), output_field=FloatField())
    
    last_weighting_date_subq = Subquery(latest_weightings.values('date')[:1])
    last_weighting_date_or_entry = Coalesce(last_weighting_date_subq, F('entry_date'))
    
    days_for_gmd_expr = last_weighting_date_subq - F('entry_date')
    days_for_gmd = ExpressionWrapper(days_for_gmd_expr / timedelta(days=1), output_field=FloatField())
    
    last_weight_kg = Coalesce(Subquery(latest_weightings.values('weight_kg')[:1]), F('entry_weight'))
    
    total_gain = last_weight_kg - F('entry_weight')
    
    gmd = total_gain / NullIf(days_for_gmd, Value(0.0), output_field=FloatField())
    
    days_since_last_weight = ExpressionWrapper((current_date - last_weighting_date_or_entry) / timedelta(days=1), output_field=FloatField())
    forecasted_weight = last_weight_kg + (gmd * days_since_last_weight)

    # --- Step 3: The Main Aggregation Query ---
    summary_query = Purchase.objects.filter(
        farm_id=farm_id, sale__isnull=True, death__isnull=True
    ).annotate(
        # The first `.annotate()` calculates the KPIs for EACH animal individually.
        _gmd=gmd,
        _current_age_months=F('entry_age') + (days_on_farm / 30.44),
        _forecasted_weight=forecasted_weight
    ).values(
        'lot'  # This performs a GROUP BY lot.
    ).annotate(
        # The second `.annotate()` performs the aggregation functions on each group.
        animal_count=Count('id'),
        male_count=Count(Case(When(sex='M', then=1))),
        female_count=Count(Case(When(sex='F', then=1))),
        # We take the average of the pre-calculated individual animal KPIs.
        average_age_months=Avg('_current_age_months'),
        average_gmd_kg=Avg('_gmd'),
        average_weight_kg=Avg('_forecasted_weight')
    ).order_by('lot')

    # --- Step 4: Serialization ---
    serializer = LotSummarySerializer(summary_query, many=True)
    return Response(serializer.data)


@api_view(['GET'])
def lot_detail_summary(request, farm_id, lot_number):
    """
    Gets a detailed summary of all active animals within a specific lot.
    """
    if not Farm.objects.filter(pk=farm_id).exists():
        return Response({"error": "Farm not found."}, status=status.HTTP_404_NOT_FOUND)

    base_query = Purchase.objects.filter(
        farm_id=farm_id,
        lot=lot_number,
        sale__isnull=True,
        death__isnull=True
    )

    # --- FINAL CORRECTED ANNOTATIONS ---
    latest_weightings = Weighting.objects.filter(animal=OuterRef('pk')).order_by('-date', '-id')
    latest_diets = DietLog.objects.filter(animal=OuterRef('pk')).order_by('-date', '-id')
    latest_locations = LocationChange.objects.filter(animal=OuterRef('pk')).order_by('-date', '-id')
    
    # --- FIX: Use TruncDate for reliable date math ---
    current_date = TruncDate(Now())
    days_on_farm = ExpressionWrapper((current_date - F('entry_date')) / timedelta(days=1), output_field=FloatField())

    last_weighting_date_subq = Subquery(latest_weightings.values('date')[:1])
    last_weighting_date_or_entry = Coalesce(last_weighting_date_subq, F('entry_date'))
    
    days_for_gmd_expr = last_weighting_date_subq - F('entry_date')
    days_for_gmd = ExpressionWrapper(days_for_gmd_expr / timedelta(days=1), output_field=FloatField())

    last_weight_kg = Coalesce(Subquery(latest_weightings.values('weight_kg')[:1]), F('entry_weight'))
    total_gain = last_weight_kg - F('entry_weight')
    gmd = total_gain / NullIf(days_for_gmd, Value(0.0), output_field=FloatField())

    days_since_last_weight = ExpressionWrapper((current_date - last_weighting_date_or_entry) / timedelta(days=1), output_field=FloatField())
    forecasted_weight = last_weight_kg + (gmd * days_since_last_weight)

    annotated_query = base_query.annotate(
        current_age_months=F('entry_age') + (days_on_farm / 30.44),
        last_weight_kg=last_weight_kg,
        average_daily_gain_kg=gmd,
        forecasted_current_weight_kg=forecasted_weight,
        current_diet_type=Subquery(latest_diets.values('diet_type')[:1]),
        days_on_farm_int=Cast(days_on_farm, IntegerField()),
        last_weighting_date=last_weighting_date_subq,
        current_diet_intake=Subquery(latest_diets.values('daily_intake_percentage')[:1]),
        current_location_id=Subquery(latest_locations.values('location_id')[:1]),
        current_sublocation_id=Subquery(latest_locations.values('sublocation_id')[:1]),
    ).order_by('ear_tag')

    serializer = AnimalSummarySerializer(annotated_query, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def active_stock_summary(request, farm_id):
    """
    Gets a complete summary of the active stock for a specific farm.
    This view returns all active animals for client-side grid functionality.
    """
    if not Farm.objects.filter(pk=farm_id).exists():
        return Response({"error": "Farm not found."}, status=status.HTTP_404_NOT_FOUND)

    active_animals_qs = Purchase.objects.filter(
        farm_id=farm_id, sale__isnull=True, death__isnull=True
    )

    # --- Define reusable annotations (same as before) ---
    latest_weightings = Weighting.objects.filter(animal=OuterRef('pk')).order_by('-date', '-id')
    latest_diets = DietLog.objects.filter(animal=OuterRef('pk')).order_by('-date', '-id')
    latest_locations = LocationChange.objects.filter(animal=OuterRef('pk')).order_by('-date', '-id')

    current_date = TruncDate(Now())
    days_on_farm = ExpressionWrapper((current_date - F('entry_date')) / timedelta(days=1), output_field=FloatField())
    
    last_weighting_date_subq = Subquery(latest_weightings.values('date')[:1])
    last_weighting_date_or_entry = Coalesce(last_weighting_date_subq, F('entry_date'))
    
    days_for_gmd_expr = last_weighting_date_subq - F('entry_date')
    days_for_gmd = ExpressionWrapper(days_for_gmd_expr / timedelta(days=1), output_field=FloatField())

    last_weight_kg = Coalesce(Subquery(latest_weightings.values('weight_kg')[:1]), F('entry_weight'))
    total_gain = last_weight_kg - F('entry_weight')
    gmd = total_gain / NullIf(days_for_gmd, Value(0.0), output_field=FloatField())

    days_since_last_weight = ExpressionWrapper((current_date - last_weighting_date_or_entry) / timedelta(days=1), output_field=FloatField())
    forecasted_weight = last_weight_kg + (gmd * days_since_last_weight)

    # --- QUERY 1: Aggregated KPIs ---
    summary_kpis_result = active_animals_qs.aggregate(
        total_active_animals=Count('id'),
        number_of_males=Count(Case(When(sex='M', then=1))),
        number_of_females=Count(Case(When(sex='F', then=1))),
        average_age_months=Avg(F('entry_age') + (days_on_farm / 30.44)),
        average_gmd_kg=Avg(gmd)
    )

    # --- QUERY 2: The detailed list of ALL animals ---
    animal_details_query = active_animals_qs.annotate(
        current_age_months=F('entry_age') + (days_on_farm / 30.44),
        last_weight_kg=last_weight_kg,
        average_daily_gain_kg=gmd,
        forecasted_current_weight_kg=forecasted_weight,
        current_diet_type=Subquery(latest_diets.values('diet_type')[:1]),
        days_on_farm_int=Cast(days_on_farm, IntegerField()),
        last_weighting_date=last_weighting_date_subq,
        current_diet_intake=Subquery(latest_diets.values('daily_intake_percentage')[:1]),
        current_location_id=Subquery(latest_locations.values('location_id')[:1]),
        current_sublocation_id=Subquery(latest_locations.values('sublocation_id')[:1]),
    ).order_by('lot', 'ear_tag')

    # --- Execute query and pre-fetch names ---
    all_animals = list(animal_details_query)

    location_ids = {animal.current_location_id for animal in all_animals if animal.current_location_id}
    sublocation_ids = {animal.current_sublocation_id for animal in all_animals if animal.current_sublocation_id}

    locations = Location.objects.filter(id__in=location_ids).values('id', 'name')
    sublocations = Sublocation.objects.filter(id__in=sublocation_ids).values('id', 'name')

    location_name_map = {loc['id']: loc['name'] for loc in locations}
    sublocation_name_map = {sub['id']: sub['name'] for sub in sublocations}
    
    serializer_context = {
        'location_name_map': location_name_map,
        'sublocation_name_map': sublocation_name_map
    }
    
    # --- FIX STARTS HERE ---
    
    # 1. Assemble a dictionary with the RAW data (model objects, not serialized data).
    final_data = {
        'summary_kpis': summary_kpis_result,
        'animals': all_animals  # Pass the list of annotated Purchase objects directly
    }
    
    # 2. Instantiate the top-level serializer, passing it the raw data and the context.
    #    It will now correctly delegate the serialization of the 'animals' list
    #    to the AnimalSummarySerializer.
    response_serializer = ActiveStockResponseSerializer(final_data, context=serializer_context)
    
    # --- FIX ENDS HERE ---

    return Response(response_serializer.data)

@api_view(['POST'])
def bulk_assign_sublocation(request, farm_id, location_id):
    """
    Finds all active animals in a parent location and assigns them all to a specified destination sublocation.
    Handles POST /api/farm/<farm_id>/location/<location_id>/bulk_assign_sublocation/
    """
    # First, a quick check to ensure the parent location from the URL is valid for this farm.
    if not Location.objects.filter(pk=location_id, farm_id=farm_id).exists():
        return Response({"error": "Parent location not found on this farm."}, status=status.HTTP_404_NOT_FOUND)

    # Use our new serializer to validate the incoming POST data.
    # We pass context so the serializer knows about the IDs from the URL for its validation logic.
    context = {'farm_id': farm_id, 'location_id': location_id}
    serializer = BulkAssignSublocationSerializer(data=request.data, context=context)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    validated_data = serializer.validated_data
    move_date = validated_data['date']
    dest_id = validated_data['destination_sublocation_id']

    # --- The Core Query ---
    # Subquery to find the latest location change for each animal.
    latest_locations = LocationChange.objects.filter(
        animal=OuterRef('pk')
    ).order_by('-date', '-id')

    # Find active animals whose LATEST location is the target parent location
    animals_to_assign = Purchase.objects.filter(
        farm_id=farm_id,
        sale__isnull=True,
        death__isnull=True
    ).annotate(
        current_location_id=Subquery(latest_locations.values('location_id')[:1]),
        current_sublocation_id=Subquery(latest_locations.values('sublocation_id')[:1])
    ).filter(
        current_location_id=location_id,
    )

    # If the query returns no animals, there's nothing to do.
    if not animals_to_assign.exists():
        return Response({'message': 'No unassigned animals found in this location.'}, status=status.HTTP_200_OK)

    # Use a database transaction and `bulk_create` for maximum performance.
    # This ensures that either all animals are moved, or none are.
    try:
        with transaction.atomic():
            new_changes = [
                LocationChange(
                    date=move_date,
                    animal=animal,
                    location_id=location_id,
                    sublocation_id=dest_id,
                    farm_id=farm_id
                )
                for animal in animals_to_assign
            ]
            LocationChange.objects.bulk_create(new_changes)
        
        return Response(
            {'message': f'Successfully assigned {len(new_changes)} animals.'},
            status=status.HTTP_201_CREATED
        )
    except Exception as e:
        # Catch any unexpected database errors.
        return Response(
            {'error': f'An unexpected error occurred during assignment: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# ==========================================================================
# 4. Developer & Data Management Views
# ==========================================================================

# --- Utility functions ported from Flask (for the seeder) ---

_historical_prices_cache = None
_sorted_dates_cache = None

def load_historical_prices():
    """
    Loads and caches historical price data from api/data/historical_prices.csv.
    This is a port of the original Flask utility function.
    """
    global _historical_prices_cache, _sorted_dates_cache
    if _historical_prices_cache is not None:
        return _historical_prices_cache, _sorted_dates_cache

    prices = {}
    # Assumes the data file is in 'api/data/historical_prices.csv'
    file_path = Path(__file__).resolve().parent / 'data' / 'historical_prices.csv'

    try:
        with open(file_path, mode='r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            # ... (the rest of the price loading logic is identical to your Flask version)
            headers = [h.lower() for h in reader.fieldnames or []]
            
            date_header = next((h for h in headers if 'date' in h), None)
            purchase_header = next((h for h in headers if 'purchase' in h), None)
            sale_header = next((h for h in headers if 'sale' in h), None)

            if not all([date_header, purchase_header, sale_header]):
                print("WARNING: CSV missing required headers: 'date', 'purchase_price', 'sale_price'.")
                _historical_prices_cache, _sorted_dates_cache = {}, []
                return {}, []

            for row in reader:
                date_str = row.get(date_header)
                purchase_str = row.get(purchase_header)
                sale_str = row.get(sale_header)

                if not date_str: continue
                try:
                    purchase_val = float(purchase_str) if purchase_str and purchase_str.strip() else None
                    sale_val = float(sale_str) if sale_str and sale_str.strip() else None

                    if purchase_val is not None or sale_val is not None:
                         prices[date_str] = {
                             'purchase': purchase_val or sale_val, 
                             'sale': sale_val or purchase_val
                        }
                except (ValueError, TypeError):
                    continue
        
        _historical_prices_cache = prices
        _sorted_dates_cache = sorted(prices.keys())
        return _historical_prices_cache, _sorted_dates_cache
        
    except FileNotFoundError:
        print(f"WARNING: Price file not found at {file_path}.")
        _historical_prices_cache, _sorted_dates_cache = {}, []
        return {}, []

def get_closest_price(target_date, price_data, sorted_dates):
    """
    Finds the price data for the date closest to the target_date.
    Ported from the original Flask utility function.
    """
    if not sorted_dates: return None
    target_date_str = target_date.isoformat()
    pos = bisect.bisect_left(sorted_dates, target_date_str)
    if pos == 0: return price_data[sorted_dates[0]]
    if pos == len(sorted_dates): return price_data[sorted_dates[-1]]
    
    date_before_str = sorted_dates[pos - 1]
    date_after_str = sorted_dates[pos]
    date_before = date.fromisoformat(date_before_str)
    date_after = date.fromisoformat(date_after_str)

    return price_data[date_before_str] if (target_date - date_before) < (date_after - target_date) else price_data[date_after_str]


@api_view(['POST'])
def seed_test_farm(request):
    """
    (For Developers) Creates a test farm with a large volume of simulated data.
    This is a destructive operation if the farm name already exists.
    It uses bulk_create for high-performance insertion of event records.
    """
    try:
        params = request.data
        farm_name = params['farm_name']
        purchases_per_year = int(params['total_animal_purchases_per_year'])
        monthly_dist = params['monthly_concentration']
        weighting_freq = int(params['weighting_frequency_days'])
        sell_after_days = int(params['sell_after_days'])
        assumed_gmd = float(params['assumed_gmd_kg'])
        sanitary_protocols_config = params['sanitary_protocols']
        initial_diet_config = params['initial_diet']
        diet_change_config = params.get('diet_change')
        num_locations = int(params['num_locations'])
        num_sublocations = int(params['num_sublocations_per_location'])
        total_farm_area_ha = float(params['total_farm_area_ha'])
        fixed_purchase_price = params.get('fixed_purchase_price')
        fixed_sale_price = params.get('fixed_sale_price_per_kg')
        years = int(params['years'])
        end_date = datetime.strptime(params['end_date'], '%Y-%m-%d').date()

    except (KeyError, ValueError) as e:
        return Response({'error': f'Invalid or missing parameter: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

    market_prices, sorted_market_dates = load_historical_prices()
    if not market_prices and (fixed_purchase_price is None or fixed_sale_price is None):
        return Response({'error': 'Historical price data missing and no fixed prices provided.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # --- 1. DESTRUCTIVE DELETION of existing farm data ---
    # This is much cleaner with the Django ORM. The related_name and CASCADE settings
    # in the models handle the deletion of all child objects automatically and efficiently.
    existing_farm = Farm.objects.filter(name=farm_name).first()
    if existing_farm:
        print(f"Farm '{farm_name}' exists. Deleting all associated data...")
        existing_farm.delete()
        print("Deletion complete.")

    # --- Use a single atomic transaction for the entire seeding process ---
    # This ensures that either the entire farm is created successfully, or no
    # changes are made to the database, guaranteeing data integrity.
    try:
        with transaction.atomic():
            print("Creating new farm and locations...")
            new_farm = Farm.objects.create(name=farm_name)

            # --- 2. Bulk Create Locations & Sublocations ---
            # Create objects in memory first, then insert them all in one DB query.
            locations_to_create = []

            random_proportions = [random.uniform(0.7, 1.3) for _ in range(num_locations)]
            total_proportion = sum(random_proportions)
            normalized_proportions = [p / total_proportion for p in random_proportions]
            
            for i in range(num_locations):
                location_area = total_farm_area_ha * normalized_proportions[i]
                locations_to_create.append(Location(
                    name=f'Pasture {i+1}', farm=new_farm, area_hectares=location_area,
                    grass_type=random.choice(['Brachiaria decumbens', 'Mombaça']),
                    location_type='Rotacionado'
                ))
            Location.objects.bulk_create(locations_to_create)
            
            # Query the newly created locations to get their IDs for sublocations
            created_locations = list(Location.objects.filter(farm=new_farm))
            
            sublocations_to_create = []
            if num_sublocations > 0:
                for loc in created_locations:
                    sublocation_area = loc.area_hectares / num_sublocations if loc.area_hectares else 0
                    for j in range(num_sublocations):
                        sublocations_to_create.append(Sublocation(
                            name=f'Paddock {j+1}', parent_location=loc, farm=new_farm, area_hectares=sublocation_area
                        ))
                Sublocation.objects.bulk_create(sublocations_to_create)

            print(f"Created {len(created_locations)} locations and {len(sublocations_to_create)} sublocations.")

            # --- 3. Main Simulation Loop & Bulk Data Generation ---
            # We will create Purchase objects one-by-one to get their IDs,
            # but collect all their numerous child event objects into lists
            # to be bulk-inserted at the end for maximum performance.
            purchases_to_create = []
            weightings_to_create = []
            location_changes_to_create = []
            diet_logs_to_create = []
            protocols_to_create = []
            sales_to_create = []
            
            start_date = end_date - timedelta(days=365 * years)
            current_date = start_date
            ear_tag_sequence = 0
            lot_counter = 0
            current_month_marker = start_date

            print("Starting data simulation loop...")
            while current_month_marker < end_date:
                # --- Monthly Purchase Logic ---
                month_key = str(current_month_marker.month)
                total_purchases_this_month = int(purchases_per_year  * float(monthly_dist.get(month_key, 0)))

                if total_purchases_this_month > 0:
                    # 1. Pick one random day in the month for the purchase event.
                    days_in_month = calendar.monthrange(current_month_marker.year, current_month_marker.month)[1]
                    purchase_day = random.randint(1, days_in_month)
                    purchase_date = date(current_month_marker.year, current_month_marker.month, purchase_day)

                    # 2. Create one new lot for this single purchase event.
                    lot_counter += 1
                    lot_sex = random.choice(['M', 'F'])
                    lot_race = random.choice(['Nelore', 'Angus', 'Brahman', 'Mestiço'])

                    # 3. Create all animals for the month in this single lot.
                    for _ in range(total_purchases_this_month):
                        # a. Increment the ear tag sequence first.
                        ear_tag_sequence += 1

                        # b. If the sequence goes past 1000, reset it and start a NEW lot.
                        #    This is the key to respecting the unique_together constraint.
                        if ear_tag_sequence > 1000:
                            ear_tag_sequence = 1
                            lot_counter += 1
                        
                        # c. Ensure the very first lot is numbered '1'.
                        if lot_counter == 0:
                            lot_counter = 1

                        # d. Now, we have a unique (ear_tag, lot) pair.
                        #    e.g., (1000, 49) will be followed by (1, 50).
                        
                        purchase_price = fixed_purchase_price
                        if purchase_price is None:
                            price_info = get_closest_price(purchase_date, market_prices, sorted_market_dates)
                            purchase_price = price_info['purchase'] if price_info else 0
                        
                        initial_weight = random.uniform(180, 250)
                        
                        p = Purchase(
                            ear_tag=str(ear_tag_sequence), # Use the cycling ear tag
                            lot=str(lot_counter),          # Use the lot that changes on rollover
                            entry_date=purchase_date,
                            entry_weight=initial_weight, 
                            sex=lot_sex, 
                            race=lot_race,
                            entry_age=random.uniform(8, 12), 
                            farm=new_farm, 
                            purchase_price=purchase_price
                        )
                        purchases_to_create.append(p)
                
                # Move marker to the first day of the next month.
                next_month = current_month_marker.month + 1
                next_year = current_month_marker.year
                if next_month > 12:
                    next_month = 1
                    next_year += 1
                current_month_marker = date(next_year, next_month, 1)

            # --- 4. Bulk Create all Purchases ---
            # This is the first major bulk operation.
            print(f"Generated {len(purchases_to_create)} purchase records. Starting bulk insert...")
            Purchase.objects.bulk_create(purchases_to_create, batch_size=500)

            # --- 5. Generate and Bulk Create Child Events ---
            # Now that purchases are in the DB, query them back to get their IDs.
            # Create a map for quick lookups to avoid re-querying inside the loop.
            all_new_purchases = Purchase.objects.filter(farm=new_farm)
            purchase_map = {p.ear_tag: p for p in all_new_purchases}
            
            print("Generating all historical event data...")
            for p in all_new_purchases:
                # Initial events
                weightings_to_create.append(Weighting(date=p.entry_date, weight_kg=p.entry_weight, animal_id=p.id, farm_id=new_farm.id))
                location_changes_to_create.append(LocationChange(date=p.entry_date, location=random.choice(created_locations), animal_id=p.id, farm_id=new_farm.id))
                diet_logs_to_create.append(DietLog(date=p.entry_date, diet_type=initial_diet_config['diet_type'], daily_intake_percentage=initial_diet_config['daily_intake_percentage'], animal_id=p.id, farm_id=new_farm.id))
                
                # Simulate life events
                sale_date = p.entry_date + timedelta(days=sell_after_days)
                last_weight = p.entry_weight
                last_weight_date = p.entry_date
                
                next_event_date = p.entry_date + timedelta(days=weighting_freq)
                while next_event_date < sale_date and next_event_date < end_date:
                    gain = (next_event_date - last_weight_date).days * (assumed_gmd * random.uniform(0.8, 1.2))
                    new_weight = last_weight + gain
                    weightings_to_create.append(Weighting(date=next_event_date, weight_kg=new_weight, animal_id=p.id, farm_id=new_farm.id))
                    last_weight, last_weight_date = new_weight, next_event_date
                    next_event_date += timedelta(days=weighting_freq)

                for protocol in sanitary_protocols_config:
                    next_protocol_date = p.entry_date + timedelta(days=protocol['frequency_days'])
                    while next_protocol_date < sale_date and next_protocol_date < end_date:
                        protocols_to_create.append(SanitaryProtocol(date=next_protocol_date, protocol_type=protocol['protocol_type'], product_name=protocol['product_name'], animal_id=p.id, farm_id=new_farm.id))
                        next_protocol_date += timedelta(days=protocol['frequency_days'])
                
                if diet_change_config:
                    diet_change_date = p.entry_date + timedelta(days=diet_change_config['days_after_purchase'])
                    if diet_change_date < sale_date and diet_change_date < end_date:
                        new_diet = diet_change_config['new_diet']
                        diet_logs_to_create.append(DietLog(date=diet_change_date, diet_type=new_diet['diet_type'], daily_intake_percentage=new_diet['daily_intake_percentage'], animal_id=p.id, farm_id=new_farm.id))
                
                if sale_date < end_date:
                    sale_price = fixed_sale_price
                    if sale_price is None:
                         price_info = get_closest_price(sale_date, market_prices, sorted_market_dates)
                         sale_price = price_info['sale'] if price_info else 0
                    
                    final_gain = (sale_date - last_weight_date).days * assumed_gmd
                    exit_weight = last_weight + final_gain
                    total_sale_price = sale_price
                    
                    sales_to_create.append(Sale(date=sale_date, sale_price=total_sale_price, animal_id=p.id, farm_id=new_farm.id))
                    weightings_to_create.append(Weighting(date=sale_date, weight_kg=exit_weight, animal_id=p.id, farm_id=new_farm.id))

            # --- 6. Final Bulk Inserts for all child events ---
            print(f"Generated {len(weightings_to_create)} weighting records. Bulk inserting...")
            Weighting.objects.bulk_create(weightings_to_create, batch_size=500)
            print(f"Generated {len(location_changes_to_create)} location changes. Bulk inserting...")
            LocationChange.objects.bulk_create(location_changes_to_create, batch_size=500)
            print(f"Generated {len(diet_logs_to_create)} diet logs. Bulk inserting...")
            DietLog.objects.bulk_create(diet_logs_to_create, batch_size=500)
            print(f"Generated {len(protocols_to_create)} sanitary protocols. Bulk inserting...")
            SanitaryProtocol.objects.bulk_create(protocols_to_create, batch_size=500)
            print(f"Generated {len(sales_to_create)} sales. Bulk inserting...")
            Sale.objects.bulk_create(sales_to_create, batch_size=500)
            
        # The 'with transaction.atomic()' block ends here. If no errors occurred,
        # all changes are committed to the database.
        
        return Response({'message': f"Successfully seeded farm '{farm_name}' with thousands of records."}, status=status.HTTP_201_CREATED)

    except Exception as e:
        # If any error occurs during the transaction, all changes are automatically rolled back.
        return Response({'error': f'An unexpected error occurred, and all changes have been rolled back. Error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def export_farms(request):
    """
    Exports all data for a given list of farm IDs into a single JSON file.
    """
    farm_ids = request.data.get('farm_ids')
    if not isinstance(farm_ids, list):
        return Response({'error': "'farm_ids' must be a list."}, status=status.HTTP_400_BAD_REQUEST)

    # Django's equivalent of eager loading for massive performance gain
    farms_to_export = Farm.objects.filter(id__in=farm_ids).prefetch_related(
        'locations__sublocations',
        'purchases__weightings',
        'purchases__protocols',
        'purchases__location_changes',
        'purchases__diet_logs',
        'purchases__sale',
        'purchases__death',
    )

    if not farms_to_export.exists():
        return Response({'error': 'No farms found for the provided IDs.'}, status=status.HTTP_404_NOT_FOUND)

    serializer = FullFarmExportSerializer(farms_to_export, many=True)
    
    export_data = {
        'export_format_version': '1.0',
        'export_date': datetime.now().isoformat(),
        'farms': serializer.data
    }
    
    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    filename = f"bovitrack_export_{timestamp}.json"

    # Use JsonResponse to create the file download response
    response = JsonResponse(export_data, json_dumps_params={'indent': 4})
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response

@api_view(['POST'])
@parser_classes([MultiPartParser])
@transaction.atomic
def import_farms(request):
    """
    Imports farm data from an uploaded JSON file within a single database transaction.
    """
    import_file = request.FILES.get('import_file')
    if not import_file:
        return Response({'error': 'No import file provided.'}, status=status.HTTP_400_BAD_REQUEST)
    if not import_file.name.endswith('.json'):
        return Response({'error': 'Invalid file type. Please upload a .json file.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        import_data = json.load(import_file)
        
        farm_id_map, location_id_map, purchase_id_map = {}, {}, {}
        imported_farm_names = []
        
        existing_farm_names = set(Farm.objects.values_list('name', flat=True))

        for farm_data in import_data.get('farms', []):
            farm_name = farm_data['name']
            if farm_name in existing_farm_names:
                continue

            # 1. Create Farm
            new_farm = Farm.objects.create(name=farm_name)
            farm_id_map[farm_data['id']] = new_farm.id
            imported_farm_names.append(farm_name)

            # 2. Create Locations & Sublocations
            for loc_data in farm_data.get('locations', []):
                new_loc = Location.objects.create(farm=new_farm, **{k: v for k, v in loc_data.items() if k not in ['id', 'sublocations']})
                location_id_map[loc_data['id']] = new_loc.id

                for sub_data in loc_data.get('sublocations', []):
                    Sublocation.objects.create(farm=new_farm, parent_location=new_loc, **{k: v for k, v in sub_data.items() if k != 'id'})

            # 3. Create Purchases and related events
            for p_data in farm_data.get('purchases', []):
                # Pop related data to handle separately
                weightings_data = p_data.pop('weightings', [])
                protocols_data = p_data.pop('protocols', [])
                loc_changes_data = p_data.pop('location_changes', [])
                diet_logs_data = p_data.pop('diet_logs', [])
                sale_data = p_data.pop('sale', None)
                death_data = p_data.pop('death', None)

                new_purchase = Purchase.objects.create(farm=new_farm, **{k: v for k, v in p_data.items() if k != 'id'})
                purchase_id_map[p_data['id']] = new_purchase.id

                for w_data in weightings_data: Weighting.objects.create(farm=new_farm, animal=new_purchase, **w_data)
                for sp_data in protocols_data: SanitaryProtocol.objects.create(farm=new_farm, animal=new_purchase, **sp_data)
                for dl_data in diet_logs_data: DietLog.objects.create(farm=new_farm, animal=new_purchase, **dl_data)
                
                for lc_data in loc_changes_data:
                    old_loc_id = lc_data.pop('location_id', None)
                    new_loc_id = location_id_map.get(old_loc_id)
                    if new_loc_id:
                        LocationChange.objects.create(farm=new_farm, animal=new_purchase, location_id=new_loc_id, **lc_data)

                if sale_data: Sale.objects.create(farm=new_farm, animal=new_purchase, **sale_data)
                if death_data: Death.objects.create(farm=new_farm, animal=new_purchase, **death_data)
        
        if not imported_farm_names:
            return Response({'message': 'Import complete. No new farms were added as existing names were found.'}, status=status.HTTP_200_OK)

        return Response({'message': f'Successfully imported data for farms: {", ".join(imported_farm_names)}'}, status=status.HTTP_201_CREATED)

    except Exception as e:
        # The @transaction.atomic decorator handles the rollback automatically on any exception.
        return Response({'error': f'An unexpected error occurred, and all changes have been rolled back. Error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)