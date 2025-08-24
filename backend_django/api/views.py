from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
# Make sure Q is imported here
from django.db import transaction
from django.db.models import Count, Subquery, OuterRef, Q, F, FloatField, Case, When, Sum
from django.db.models.functions import Coalesce
from .models import Farm, Location, Purchase, LocationChange, Sublocation, Weighting, DietLog, Sale, Death, SanitaryProtocol
from .serializers import (FarmSerializer, LocationSerializer, SublocationSerializer, 
                    PurchaseCreateSerializer, PurchaseListSerializer, WeightingSerializer, 
                    LocationChangeSerializer, DietLogSerializer, SanitaryProtocolSerializer, 
                    SaleCreateSerializer, SaleSerializer)   # We will add more serializers here later
from datetime import date
# Create your views here.

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

@api_view(['GET'])
def location_list(request, farm_id):
    """
    API view to retrieve a list of locations for a farm, enriched with
    database-calculated KPIs for both locations and sublocations.
    This version uses separate, optimized queries for clarity and robustness.
    """
    # --- Step 1: Get data for all active animals on the farm ---
    # We fetch the essential components needed for all our calculations.
    active_animals_qs = Purchase.objects.filter(
        farm_id=farm_id, sale__isnull=True, death__isnull=True
    ).annotate(
        # Get the ID of the animal's latest location
        current_location_id=Subquery(
            LocationChange.objects.filter(animal=OuterRef('pk')).order_by('-date', '-id').values('location_id')[:1]
        ),
        # Get the ID of the animal's latest sublocation
        current_sublocation_id=Subquery(
            LocationChange.objects.filter(animal=OuterRef('pk')).order_by('-date', '-id').values('sublocation_id')[:1]
        ),
        # Get the animal's latest weight
        last_weight=Subquery(
            Weighting.objects.filter(animal=OuterRef('pk')).order_by('-date', '-id').values('weight_kg')[:1]
        ),
        # Get the date of the animal's latest weight
        last_weight_date=Subquery(
            Weighting.objects.filter(animal=OuterRef('pk')).order_by('-date', '-id').values('date')[:1]
        )
    )

    # --- Step 2: Process the data in Python ---
    today = date.today()
    location_kpis = {}
    sublocation_kpis = {}

    for animal in active_animals_qs:
        loc_id = animal.current_location_id
        subloc_id = animal.current_sublocation_id

        # Initialize dictionaries if needed
        if loc_id and loc_id not in location_kpis:
            location_kpis[loc_id] = {'animal_count': 0, 'total_actual': 0.0, 'total_forecasted': 0.0}
        if subloc_id and subloc_id not in sublocation_kpis:
            sublocation_kpis[subloc_id] = {'animal_count': 0}

        # Calculate GMD and Forecasted Weight
        last_w = animal.last_weight or animal.entry_weight
        last_w_date = animal.last_weight_date or animal.entry_date
        days_for_gmd = (last_w_date - animal.entry_date).days
        gain = last_w - animal.entry_weight
        gmd = (gain / days_for_gmd) if days_for_gmd > 0 else 0.0
        days_since_weigh = (today - last_w_date).days
        forecasted_w = last_w + (gmd * days_since_weigh)

        # Aggregate data
        if loc_id:
            location_kpis[loc_id]['animal_count'] += 1
            location_kpis[loc_id]['total_actual'] += last_w
            location_kpis[loc_id]['total_forecasted'] += forecasted_w
        if subloc_id:
            sublocation_kpis[subloc_id]['animal_count'] += 1

    # --- Step 3: Get Location Objects and Serialize ---
    locations = Location.objects.filter(farm_id=farm_id).prefetch_related('sublocations').order_by('name')

    context = {
        'location_kpis': location_kpis,
        'sublocation_counts': sublocation_kpis,
    }
    
    serializer = LocationSerializer(locations, many=True, context=context)
    return Response(serializer.data)

@api_view(['GET', 'POST'])
def purchase_list(request, farm_id):
    """
    API view to list all purchases for a farm or create a new one.
    - Handles GET /api/farm/<farm_id>/purchases/
    - Handles POST /api/farm/<farm_id>/purchases/
    """
    # First, check if the farm itself exists.
    try:
        Farm.objects.get(pk=farm_id)
    except Farm.DoesNotExist:
        return Response({"error": "Farm not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        purchases = Purchase.objects.filter(farm_id=farm_id).order_by('-entry_date')
        serializer = PurchaseListSerializer(purchases, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        # Pass the farm_id from the URL into the serializer's context
        # so our custom validation can use it.
        context = {'farm_id': farm_id}
        serializer = PurchaseCreateSerializer(data=request.data, context=context)

        if serializer.is_valid():
            # validated_data contains the clean, validated input data
            validated_data = serializer.validated_data
            
            # Pop the extra fields that are not on the Purchase model itself
            location_id = validated_data.pop('location_id')
            initial_diet_type = validated_data.pop('initial_diet_type', None)
            daily_intake_percentage = validated_data.pop('daily_intake_percentage', None)
            protocols_data = validated_data.pop('sanitary_protocols', [])

            try:
                # Use a transaction to ensure all or nothing is saved.
                with transaction.atomic():
                    # 1. Create the main Purchase object
                    # We add farm_id here before creating the object.
                    new_purchase = Purchase.objects.create(farm_id=farm_id, **validated_data)

                    # 2. Create the initial Weighting
                    Weighting.objects.create(
                        farm_id=farm_id,
                        animal=new_purchase,
                        date=new_purchase.entry_date,
                        weight_kg=new_purchase.entry_weight
                    )

                    # 3. Create the initial LocationChange
                    LocationChange.objects.create(
                        farm_id=farm_id,
                        animal=new_purchase,
                        date=new_purchase.entry_date,
                        location_id=location_id
                    )

                    # 4. Create the initial DietLog (if provided)
                    if initial_diet_type:
                        DietLog.objects.create(
                            farm_id=farm_id,
                            animal=new_purchase,
                            date=new_purchase.entry_date,
                            diet_type=initial_diet_type,
                            daily_intake_percentage=daily_intake_percentage
                        )
                    
                    # 5. Create SanitaryProtocols (if provided)
                    for protocol_data in protocols_data:
                        SanitaryProtocol.objects.create(
                            farm_id=farm_id,
                            animal=new_purchase,
                            **protocol_data
                        )
                
                # After the transaction is successfully committed, return the created purchase.
                # Use the read-only serializer for the response.
                response_serializer = PurchaseListSerializer(new_purchase)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)

            except Exception as e:
                # If anything fails inside the transaction, it's automatically rolled back.
                return Response(
                    {"error": f"An unexpected error occurred during save: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        # If the initial validation fails, return the errors.
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def sale_list(request, farm_id):
    """
    API view to list all sales for a specific farm.
    """
    # Use select_related('animal') to fetch the related Purchase object
    # in the same database query. This is a crucial performance optimization.
    sales = Sale.objects.filter(farm_id=farm_id).select_related('animal').order_by('-date')
    
    serializer = SaleSerializer(sales, many=True)
    return Response(serializer.data)

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