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


class WeightingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Weighting
        # We only need fields for creation, not the reverse relationships.
        fields = ['id', 'date', 'weight_kg']

class LocationChangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocationChange
        fields = ['id', 'date', 'location', 'sublocation']

class DietLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = DietLog
        fields = ['id', 'date', 'diet_type', 'daily_intake_percentage']

class SanitaryProtocolSerializer(serializers.ModelSerializer):
    class Meta:
        model = SanitaryProtocol
        fields = [
            'id', 'date', 'protocol_type', 'product_name', 'dosage', 'invoice_number'
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
    # --- Renamed and Added Fields ---
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