from rest_framework import serializers
from .models import Farm, Location, Purchase, Sublocation, Weighting, SanitaryProtocol, LocationChange, DietLog, Death, Sale # We will add more models here later

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