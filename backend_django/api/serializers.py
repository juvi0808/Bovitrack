from rest_framework import serializers
from .models import Farm, Location, Purchase, Sublocation, Weighting, SanitaryProtocol, LocationChange, DietLog, Death, Sale # We will add more models here later
from datetime import date

class FarmSerializer(serializers.ModelSerializer):
    """
    Serializer for the Farm model.
    It will convert Farm model instances into JSON format.
    """
    class Meta:
        model = Farm
        fields = ['id', 'name']

class SublocationSerializer(serializers.ModelSerializer):
    animal_count = serializers.SerializerMethodField()
    geo_json_data = serializers.SerializerMethodField()

    class Meta:
        model = Sublocation
        fields = ['id', 'name', 'area_hectares', 'animal_count', 'geo_json_data', 'parent_location_id']

    def get_animal_count(self, obj):
        # The view now provides sublocation KPIs directly
        counts = self.context.get('sublocation_counts', {})
        return counts.get(obj.id, {}).get('animal_count', 0)

    def get_geo_json_data(self, obj):
        return obj.geo_json_data if obj.geo_json_data else None

class LocationSerializer(serializers.ModelSerializer):
    sublocations = SublocationSerializer(many=True, read_only=True)
    kpis = serializers.SerializerMethodField()
    geo_json_data = serializers.SerializerMethodField()

    class Meta:
        model = Location
        fields = [
            'id', 'name', 'area_hectares', 'grass_type', 'location_type',
            'geo_json_data', 'farm_id', 'sublocations', 'kpis',
        ]
    
    def get_geo_json_data(self, obj):
        return obj.geo_json_data if obj.geo_json_data else None

    def get_kpis(self, obj):
        ANIMAL_UNIT_WEIGHT_KG = 450.0
        kpis_dict = self.context.get('location_kpis', {})
        kpi_data = kpis_dict.get(obj.id, {
            'animal_count': 0, 'total_actual': 0.0, 'total_forecasted': 0.0
        })

        kpis = {
            'animal_count': kpi_data['animal_count'],
            'capacity_rate_actual_ua_ha': None,
            'capacity_rate_forecasted_ua_ha': None,
        }

        if obj.area_hectares and obj.area_hectares > 0:
            if kpi_data['total_actual'] > 0:
                ua_actual = kpi_data['total_actual'] / ANIMAL_UNIT_WEIGHT_KG
                kpis['capacity_rate_actual_ua_ha'] = round(ua_actual / obj.area_hectares, 2)
            if kpi_data['total_forecasted'] > 0:
                ua_forecasted = kpi_data['total_forecasted'] / ANIMAL_UNIT_WEIGHT_KG
                kpis['capacity_rate_forecasted_ua_ha'] = round(ua_forecasted / obj.area_hectares, 2)
        
        return kpis

class LocationCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for CREATING and UPDATING locations.
    Contains only the fields that are directly writeable by the user.
    """
    class Meta:
        model = Location
        fields = [
            'name', 'area_hectares', 'grass_type', 'location_type', 'geo_json_data'
        ]

    def validate_name(self, value):
        """
        Check that a location with this name does not already exist on this farm.
        """
        farm_id = self.context.get('farm_id')
        # On update, self.instance will be the location being updated.
        # We exclude it from the queryset to allow a user to save without changing the name.
        queryset = Location.objects.filter(farm_id=farm_id, name__iexact=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError(f"A location with the name '{value}' already exists on this farm.")
        return value

class AnimalSummarySerializer(serializers.ModelSerializer):
    """
    Serializer for the detailed animal list within the location summary.
    Calculates and includes individual animal KPIs.
    """
    kpis = serializers.SerializerMethodField()
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Purchase
        # Add farm_id to the top-level fields to match Flask output
        fields = [
            'id', 'farm_id', 'ear_tag', 'lot', 'entry_date', 'entry_weight', 'sex', 'entry_age',
            'purchase_price', 'race', 'kpis'
        ]

    def get_kpis(self, obj):
        # The view now annotates all required values onto the queryset object.
        last_w_date = getattr(obj, 'last_weighting_date', None)

        return {
            'average_daily_gain_kg': getattr(obj, 'average_daily_gain_kg', None),
            'current_age_months': getattr(obj, 'current_age_months', None),
            'current_diet_intake': getattr(obj, 'current_diet_intake', None),
            'current_diet_type': getattr(obj, 'current_diet_type', None),
            'current_location_id': getattr(obj, 'current_location_id', None),
            'current_location_name': getattr(obj, 'current_location_name', None),
            'current_sublocation_id': getattr(obj, 'current_sublocation_id', None),
            'current_sublocation_name': getattr(obj, 'current_sublocation_name', None),
            'days_on_farm': getattr(obj, 'days_on_farm_int', None),
            'forecasted_current_weight_kg': getattr(obj, 'forecasted_current_weight_kg', None),
            'last_weight_kg': getattr(obj, 'last_weight_kg', None),
            'last_weighting_date': last_w_date.isoformat() if last_w_date else None,
            'status': "Active" # Since this search only returns active animals
        }

class LocationSummarySerializer(serializers.Serializer):
    """
    Top-level serializer for the location summary response.
    Defines the final JSON structure: {'location_details': {...}, 'animals': [...]}.
    """
    location_details = LocationSerializer()
    animals = AnimalSummarySerializer(many=True)

class SublocationSerializer(serializers.ModelSerializer):
    """
    Simple serializer for LISTING or RETRIEVING a sublocation.
    Matches the basic structure of the old Flask API's to_dict().
    """
    # Renaming 'parent_location_id' to match the old API's 'location_id'
    location_id = serializers.IntegerField(source='parent_location_id', read_only=True)
    
    class Meta:
        model = Sublocation
        fields = ['id', 'name', 'area_hectares', 'geo_json_data', 'location_id']


class SublocationCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for CREATING and UPDATING a sublocation.
    """
    class Meta:
        model = Sublocation
        fields = ['name', 'area_hectares', 'geo_json_data']

    def validate_name(self, value):
        """
        Check that a sublocation with this name does not already exist
        within the same parent location.
        """
        location_id = self.context.get('location_id')
        queryset = Sublocation.objects.filter(parent_location_id=location_id, name__iexact=value)

        # On update, exclude the current instance from the check
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise serializers.ValidationError(f"A sublocation with the name '{value}' already exists in this location.")
        return value


class WeightingSerializer(serializers.ModelSerializer):
    """
    Serializer for the Weighting model, designed for read operations.
    It fetches related animal data (ear_tag, lot) for a rich, flat JSON response,
    matching the original Flask API structure.
    """
    # Use 'source' to access attributes on the related 'animal' model.
    # This relies on the view pre-fetching this data with select_related() for performance.
    ear_tag = serializers.CharField(source='animal.ear_tag', read_only=True)
    lot = serializers.CharField(source='animal.lot', read_only=True)

    class Meta:
        model = Weighting
        fields = [
            'id', 'date', 'weight_kg', 'animal_id', 'farm_id',
            'ear_tag', 'lot'
        ]

class WeightingCreateSerializer(serializers.ModelSerializer):
    """
    Serializer specifically for CREATING a new Weighting record.
    """
    class Meta:
        model = Weighting
        # Only the fields required from the user's POST request.
        # 'animal' and 'farm' will be assigned in the view.
        fields = ['date', 'weight_kg']

class LocationChangeSerializer(serializers.ModelSerializer):
    """
    Serializer for LISTING location changes.
    """
    location_change_id = serializers.IntegerField(source='id', read_only=True)
    ear_tag = serializers.CharField(source='animal.ear_tag', read_only=True)
    lot = serializers.CharField(source='animal.lot', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    sublocation_name = serializers.CharField(source='sublocation.name', read_only=True, allow_null=True)

    class Meta:
        model = LocationChange
        fields = [
            'location_change_id', 'date', 'ear_tag', 'lot',
            'location_name', 'location_id', 'sublocation_name',
            'sublocation_id', 'animal_id', 'farm_id'
        ]

class LocationChangeCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for CREATING a new location change.
    Includes validation for optional weight and sublocation.
    """
    weight_kg = serializers.FloatField(required=False, write_only=True)
    # location_id and sublocation_id are already on the model,
    # so we just need to ensure they are writeable.
    location_id = serializers.IntegerField()
    sublocation_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = LocationChange
        fields = ['date', 'location_id', 'sublocation_id', 'weight_kg']

    def validate(self, data):
        """
        Custom multi-field validation.
        """
        farm_id = self.context.get('farm_id')
        location_id = data.get('location_id')
        sublocation_id = data.get('sublocation_id')

        # 1. Validate that the parent location exists on this farm.
        try:
            location = Location.objects.get(pk=location_id, farm_id=farm_id)
        except Location.DoesNotExist:
            raise serializers.ValidationError({"location_id": f"Location with id {location_id} not found on this farm."})

        # 2. If a sublocation is provided, validate it.
        if sublocation_id:
            try:
                sublocation = Sublocation.objects.get(pk=sublocation_id, farm_id=farm_id)
                # 3. Ensure the sublocation belongs to the specified parent location.
                if sublocation.parent_location_id != location.id:
                    raise serializers.ValidationError({"sublocation_id": "Sublocation does not belong to the specified parent location."})
            except Sublocation.DoesNotExist:
                raise serializers.ValidationError({"sublocation_id": f"Sublocation with id {sublocation_id} not found on this farm."})
        
        return data


class DietLogSerializer(serializers.ModelSerializer):
    """
    Serializer for LISTING diet logs.
    """
    diet_log_id = serializers.IntegerField(source='id', read_only=True)
    ear_tag = serializers.CharField(source='animal.ear_tag', read_only=True)
    lot = serializers.CharField(source='animal.lot', read_only=True)

    class Meta:
        model = DietLog
        fields = [
            'diet_log_id', 'date', 'ear_tag', 'lot', 'diet_type',
            'daily_intake_percentage', 'animal_id', 'farm_id'
        ]

class DietLogCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for CREATING a new diet log.
    Includes the optional weight field.
    """
    weight_kg = serializers.FloatField(required=False, write_only=True)

    class Meta:
        model = DietLog
        fields = ['date', 'diet_type', 'daily_intake_percentage', 'weight_kg']

class SanitaryProtocolSerializer(serializers.ModelSerializer):
    """
    Serializer for LISTING sanitary protocols.
    Includes read-only fields from the related animal for a rich response.
    """
    ear_tag = serializers.CharField(source='animal.ear_tag', read_only=True)
    lot = serializers.CharField(source='animal.lot', read_only=True)
    protocol_id = serializers.IntegerField(source='id', read_only=True)

    class Meta:
        model = SanitaryProtocol
        fields = [
            'protocol_id', 'date', 'ear_tag', 'lot', 'protocol_type',
            'product_name', 'invoice_number', 'dosage', 'animal_id', 'farm_id'
        ]

class SanitaryProtocolCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for CREATING sanitary protocols within a batch.
    """
    class Meta:
        model = SanitaryProtocol
        # Fields required for each protocol object in the POST request's list.
        fields = [
            'date', 'protocol_type', 'product_name', 'dosage', 'invoice_number'
        ]

# --- Serializers for the Purchase Endpoint ---

class PurchaseCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for CREATING a purchase. It accepts nested data for related records.
    """
    # --- Fields for related data that are NOT on the Purchase model ---
    location_id = serializers.IntegerField(write_only=True, required=True)
    initial_diet_type = serializers.CharField(write_only=True, required=False, allow_blank=True)
    daily_intake_percentage = serializers.FloatField(write_only=True, required=False, allow_null=True)
    
    # --- Nested Serializer for Sanitary Protocols ---
    # This tells DRF to expect a list of protocol objects and to validate
    # each one using the SanitaryProtocolSerializer.
    sanitary_protocols = SanitaryProtocolSerializer(many=True, required=False, write_only=True)

    class Meta:
        model = Purchase
        fields = [
            'id', 'ear_tag', 'lot', 'entry_date', 'entry_weight', 'sex', 'entry_age',
            'purchase_price', 'race',
            # Add our extra, write-only fields here:
            'location_id', 'initial_diet_type', 'daily_intake_percentage',
            'sanitary_protocols'
        ]
        read_only_fields = ['id']

    def validate_location_id(self, value):
        """
        Custom validation to ensure the provided location_id exists and
        belongs to the farm that will be assigned in the view.
        """
        farm_id = self.context.get('farm_id')
        if not Location.objects.filter(pk=value, farm_id=farm_id).exists():
            raise serializers.ValidationError(f"Location with id {value} not found on this farm.")
        return value


class PurchaseListSerializer(serializers.ModelSerializer):
    """
    Serializer for LISTING purchases (read-only).
    """
    class Meta:
        model = Purchase
        # Simple list of fields to display in the purchase history grid.
        fields = [
            'id', 'ear_tag', 'lot', 'entry_date', 'entry_weight', 'sex', 'entry_age',
            'purchase_price', 'race', 'farm_id'
        ]

class SaleSerializer(serializers.ModelSerializer):
    """
    Serializer for the Sale model, enriched with calculated KPIs.
    """
    sale_id = serializers.IntegerField(source='id', read_only=True)
    animal_id = serializers.IntegerField(source='animal.id', read_only=True)
    farm_id = serializers.IntegerField(source='animal.farm_id', read_only=True)
    exit_date = serializers.DateField(source='date', read_only=True)
    exit_price = serializers.FloatField(source='sale_price', read_only=True)

    # --- Fields from the related Animal object ---
    ear_tag = serializers.CharField(source='animal.ear_tag', read_only=True)
    lot = serializers.CharField(source='animal.lot', read_only=True)
    race = serializers.CharField(source='animal.race', read_only=True)
    sex = serializers.CharField(source='animal.sex', read_only=True)
    entry_date = serializers.DateField(source='animal.entry_date', read_only=True)
    entry_weight = serializers.FloatField(source='animal.entry_weight', read_only=True)
    entry_price = serializers.FloatField(source='animal.purchase_price', read_only=True)
    
    # --- Calculated KPI Fields ---
    days_on_farm = serializers.SerializerMethodField()
    exit_weight = serializers.SerializerMethodField()
    gmd_kg_day = serializers.SerializerMethodField()
    exit_age_months = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        # This list now defines the exact fields AND order of the final JSON output.
        fields = [
            'animal_id', 'days_on_farm', 'ear_tag', 'entry_date', 'entry_price',
            'entry_weight', 'exit_age_months', 'exit_date', 'exit_price',
            'exit_weight', 'farm_id', 'gmd_kg_day', 'lot', 'race', 'sale_id', 'sex'
        ]

    def get_days_on_farm(self, obj):
        return (obj.date - obj.animal.entry_date).days

    def get_exit_weight(self, obj):
        # Find the weighting that occurred on the same day as the sale
        exit_weighting = Weighting.objects.filter(animal=obj.animal, date=obj.date).first()
        return exit_weighting.weight_kg if exit_weighting else None

    def get_gmd_kg_day(self, obj):
        days = self.get_days_on_farm(obj)
        exit_w = self.get_exit_weight(obj)
        if days > 0 and exit_w is not None:
            total_gain = exit_w - obj.animal.entry_weight
            return round(total_gain / days, 3)
        return 0.0

    def get_exit_age_months(self, obj):
        days = self.get_days_on_farm(obj)
        return round(obj.animal.entry_age + (days / 30.44), 2)

class SaleCreateSerializer(serializers.ModelSerializer):
    """
    Serializer specifically for CREATING a new Sale.
    It includes the exit_weight which is not on the Sale model itself.
    """
    # This field is required for the new, final Weighting, but not part of the Sale model.
    exit_weight = serializers.FloatField(required=True, write_only=True)

    class Meta:
        model = Sale
        fields = ['date', 'sale_price', 'exit_weight']

class DeathSerializer(serializers.ModelSerializer):
    """
    Serializer for LISTING death records.
    """
    death_id = serializers.IntegerField(source='id', read_only=True)
    ear_tag = serializers.CharField(source='animal.ear_tag', read_only=True)
    lot = serializers.CharField(source='animal.lot', read_only=True)

    class Meta:
        model = Death
        fields = [
            'death_id', 'date', 'ear_tag', 'lot', 'cause',
            'animal_id', 'farm_id'
        ]

class DeathCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for CREATING a new death record.
    """
    class Meta:
        model = Death
        fields = ['date', 'cause']

class WeightHistoryEntrySerializer(serializers.Serializer):
    """
    Serializes a single, pre-calculated entry in an animal's weight history.
    This is not a ModelSerializer because the GMD fields are calculated in Python.
    """
    date = serializers.DateField()
    weight_kg = serializers.FloatField()
    gmd_accumulated_grams = serializers.FloatField()
    gmd_period_grams = serializers.FloatField()


class AnimalKpiSerializer(serializers.Serializer):
    """
    Serializes the calculated Key Performance Indicators (KPIs) for an animal.
    This is not a ModelSerializer as all fields are computed.
    """
    average_daily_gain_kg = serializers.FloatField()
    last_weight_kg = serializers.FloatField()
    last_weighting_date = serializers.DateField()
    current_age_months = serializers.FloatField()
    forecasted_current_weight_kg = serializers.FloatField(allow_null=True)
    status = serializers.CharField()
    days_on_farm = serializers.IntegerField()
    current_location_name = serializers.CharField(allow_null=True)
    current_location_id = serializers.IntegerField(allow_null=True)
    current_sublocation_name = serializers.CharField(allow_null=True)
    current_sublocation_id = serializers.IntegerField(allow_null=True)
    current_diet_type = serializers.CharField(allow_null=True)
    current_diet_intake = serializers.FloatField(allow_null=True)


class AnimalMasterRecordSerializer(serializers.ModelSerializer):
    """
    The main serializer for the animal master record endpoint.
    It assembles the complete, nested JSON structure by using other serializers
    and custom methods, implementing the "Smart Hydration" pattern.
    """
    purchase_details = PurchaseListSerializer(source='*')
    exit_details = serializers.SerializerMethodField()
    calculated_kpis = serializers.SerializerMethodField()
    weight_history = serializers.SerializerMethodField()
    protocol_history = SanitaryProtocolSerializer(source='protocols', many=True)
    location_history = LocationChangeSerializer(source='location_changes', many=True)
    diet_history = DietLogSerializer(source='diet_logs', many=True)

    class Meta:
        model = Purchase
        fields = [
            'purchase_details',
            'exit_details',
            'calculated_kpis',
            'weight_history',
            'protocol_history',
            'location_history',
            'diet_history',
        ]

    def get_exit_details(self, obj):
        """
        Checks if the animal was sold or has died and returns the
        appropriate serialized data.
        """
        if hasattr(obj, 'sale') and obj.sale:
            serializer = SaleSerializer(obj.sale)
            # Add profit/loss calculation, matching the Flask logic
            data = serializer.data
            if obj.purchase_price:
                data['profit_loss'] = data['exit_price'] - obj.purchase_price
            else:
                data['profit_loss'] = None
            return data
        if hasattr(obj, 'death') and obj.death:
            return DeathSerializer(obj.death).data
        return None

    def get_weight_history(self, obj):
        """
        Ports the `calculate_weight_history_with_gmd` logic from Flask.
        It takes the prefetched weighting records, calculates GMDs,
        and returns the enriched history.
        """
        all_weight_events = [{'date': obj.entry_date, 'weight_kg': obj.entry_weight}]
        all_weight_events.extend(
            {'date': w.date, 'weight_kg': w.weight_kg} for w in obj.weightings.all()
        )

        unique_events = [dict(t) for t in {tuple(d.items()) for d in all_weight_events}]
        sorted_events = sorted(unique_events, key=lambda w: w['date'])

        enriched_history = []
        if not sorted_events:
            return []

        first_event = sorted_events[0]
        for i, current_event in enumerate(sorted_events):
            days_since_start = (current_event['date'] - first_event['date']).days
            gain_since_start = current_event['weight_kg'] - first_event['weight_kg']
            gmd_accumulated = (gain_since_start / days_since_start) if days_since_start > 0 else 0.0

            gmd_period = 0.0
            if i > 0:
                previous_event = sorted_events[i - 1]
                days_between = (current_event['date'] - previous_event['date']).days
                gain_between = current_event['weight_kg'] - previous_event['weight_kg']
                gmd_period = (gain_between / days_between) if days_between > 0 else 0.0

            enriched_history.append({
                'date': current_event['date'],
                'weight_kg': round(current_event['weight_kg'], 2),
                'gmd_accumulated_grams': round(gmd_accumulated, 3),
                'gmd_period_grams': round(gmd_period, 3),
            })
        
        # We use the simple entry serializer here as the logic is already done
        return WeightHistoryEntrySerializer(enriched_history, many=True).data

    def get_calculated_kpis(self, obj):
        """
        Ports the `calculate_kpis` logic from the Flask Purchase model.
        This performs all KPI calculations in Python after the data
        has been efficiently fetched.
        """
        today = date.today()
        kpis = {}

        # --- Location & Diet ---
        latest_change = obj.location_changes.order_by('-date', '-id').first()
        latest_diet = obj.diet_logs.order_by('-date', '-id').first()
        kpis['current_location_name'] = latest_change.location.name if latest_change else None
        kpis['current_location_id'] = latest_change.location_id if latest_change else None
        kpis['current_sublocation_name'] = latest_change.sublocation.name if latest_change and latest_change.sublocation else None
        kpis['current_sublocation_id'] = latest_change.sublocation_id if latest_change and latest_change.sublocation else None
        kpis['current_diet_type'] = latest_diet.diet_type if latest_diet else None
        kpis['current_diet_intake'] = latest_diet.daily_intake_percentage if latest_diet else None

        # --- GMD and Last Weight ---
        sorted_weights = sorted(obj.weightings.all(), key=lambda w: w.date)
        gmd = 0.0
        last_weight = obj.entry_weight
        last_weighting_date = obj.entry_date

        if sorted_weights:
            last_weighting_obj = sorted_weights[-1]
            last_weight = last_weighting_obj.weight_kg
            last_weighting_date = last_weighting_obj.date
            
            total_days = (last_weighting_date - obj.entry_date).days
            total_gain = last_weight - obj.entry_weight
            if total_days > 0:
                gmd = total_gain / total_days

        kpis['average_daily_gain_kg'] = round(gmd, 3)
        kpis['last_weight_kg'] = round(last_weight, 2)
        kpis['last_weighting_date'] = last_weighting_date

        # --- Status-Aware Calculations ---
        if hasattr(obj, 'sale') and obj.sale:
            days_on_farm = (obj.sale.date - obj.entry_date).days
            kpis['current_age_months'] = round(obj.entry_age + (days_on_farm / 30.44), 2)
            kpis['forecasted_current_weight_kg'] = None
            kpis['status'] = 'Sold'
        elif hasattr(obj, 'death') and obj.death:
            days_on_farm = (obj.death.date - obj.entry_date).days
            kpis['current_age_months'] = round(obj.entry_age + (days_on_farm / 30.44), 2)
            kpis['forecasted_current_weight_kg'] = None
            kpis['status'] = 'Dead'
        else:
            days_on_farm = (today - obj.entry_date).days
            kpis['current_age_months'] = round(obj.entry_age + (days_on_farm / 30.44), 2)
            days_since_last_weight = (today - last_weighting_date).days
            forecasted_gain = days_since_last_weight * gmd
            kpis['forecasted_current_weight_kg'] = round(last_weight + forecasted_gain, 2)
            kpis['status'] = 'Active'
            
        kpis['days_on_farm'] = days_on_farm
        
        # Use the dedicated KPI serializer to ensure structure
        return AnimalKpiSerializer(kpis).data

class LotSummarySerializer(serializers.Serializer):
    """
    Serializer for the aggregated lot summary data.
    This is not a ModelSerializer as the data comes from an aggregate query.
    """
    lot_number = serializers.CharField(source='lot')
    animal_count = serializers.IntegerField()
    male_count = serializers.IntegerField()
    female_count = serializers.IntegerField()
    average_age_months = serializers.FloatField()
    average_gmd_kg = serializers.FloatField()
    average_weight_kg = serializers.FloatField()

class ActiveStockSummaryKpiSerializer(serializers.Serializer):
    """
    Serializer for the aggregated KPIs of the entire active herd.
    The field names are chosen to exactly match the Flask API output.
    """
    total_active_animals = serializers.IntegerField()
    number_of_males = serializers.IntegerField()
    number_of_females = serializers.IntegerField()
    average_age_months = serializers.FloatField()
    average_gmd_kg_day = serializers.FloatField(source='average_gmd_kg') # Map source field from annotation


class ActiveStockResponseSerializer(serializers.Serializer):
    """
    Top-level serializer that defines the final JSON structure for the
    active stock summary endpoint.
    """
    summary_kpis = ActiveStockSummaryKpiSerializer()
    # We reuse the AnimalSummarySerializer for the list of animals, which is
    # a perfect example of the DRY (Don't Repeat Yourself) principle.
    animals = AnimalSummarySerializer(many=True)

class BulkAssignSublocationSerializer(serializers.Serializer):
    """
    Serializer for validating the data for a bulk sublocation assignment.
    It's not a ModelSerializer because it doesn't map directly to a model.
    """
    date = serializers.DateField()
    destination_sublocation_id = serializers.IntegerField()

    def validate(self, data):
        """
        Performs cross-field validation to ensure the destination sublocation
        is valid and belongs to the parent location specified in the URL.
        """
        # The view passes these IDs from the URL into the serializer's context.
        farm_id = self.context.get('farm_id')
        location_id = self.context.get('location_id')
        dest_sublocation_id = data.get('destination_sublocation_id')

        # 1. Check that the destination sublocation exists and belongs to the farm.
        try:
            dest_sublocation = Sublocation.objects.get(pk=dest_sublocation_id, farm_id=farm_id)
        except Sublocation.DoesNotExist:
            raise serializers.ValidationError({
                "destination_sublocation_id": f"Destination sublocation with id {dest_sublocation_id} not found on this farm."
            })

        # 2. Check that the destination sublocation belongs to the parent location from the URL.
        if dest_sublocation.parent_location_id != location_id:
            raise serializers.ValidationError({
                "destination_sublocation_id": "Destination sublocation does not belong to the specified parent location."
            })

        return data