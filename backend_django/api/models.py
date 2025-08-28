from django.db import models

# ==========================================================================
# 1. Core Organizational Models
# ==========================================================================

class Farm(models.Model):
    """Represents a single farm, the top-level container for all data."""
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Location(models.Model):
    """Represents a physical location on a farm (e.g., pasture, feedlot)."""
    name = models.CharField(max_length=100, blank=False, null=False)
    area_hectares = models.FloatField(null=True, blank=True)
    grass_type = models.CharField(max_length=50, null=True, blank=True)
    location_type = models.CharField(max_length=50, null=True, blank=True)
    geo_json_data = models.TextField(null=True, blank=True)
    
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='locations')

    def __str__(self):
        return f'{self.name} ({self.farm.name})'

class Sublocation(models.Model):
    """Represents a subdivision within a parent Location (e.g., a paddock)."""
    name = models.CharField(max_length=100, blank=False, null=False)
    area_hectares = models.FloatField(null=True, blank=True)
    geo_json_data = models.TextField(null=True, blank=True)
    
    parent_location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='sublocations')
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='farm_sublocations')

    def __str__(self):
        return f'{self.name} (in {self.parent_location.name})'

# ==========================================================================
# 2. Animal and Event Models
# ==========================================================================

class Purchase(models.Model):
    """Represents the entry record of a single animal into a farm."""
    ear_tag = models.CharField(max_length=20, blank=False, null=False, db_index=True) # INDEX: Crucial for searching.
    lot = models.CharField(max_length=20, blank=False, null=False, db_index=True) # INDEX: Crucial for lot lookups.
    entry_date = models.DateField(db_index=True) # INDEX: Crucial for date-based queries.
    entry_weight = models.FloatField()
    sex = models.CharField(max_length=1)
    entry_age = models.FloatField()
    purchase_price = models.FloatField(null=True, blank=True)
    race = models.CharField(max_length=50, null=True, blank=True)
    
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='purchases')

    class Meta:
        unique_together = [['ear_tag', 'lot', 'farm']]

    def __str__(self):
        return self.ear_tag
    
class Weighting(models.Model):
    """Represents a single weight measurement event for an animal."""
    date = models.DateField(db_index=True) # INDEX: Crucial for date-based queries.
    weight_kg = models.FloatField()
    
    animal = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name='weightings')
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='weightings')

    def __str__(self):
        return f'{self.animal.ear_tag} - {self.weight_kg}kg on {self.date}'

class Sale(models.Model):
    """Represents the sale event of an animal, marking its exit from the farm."""
    date = models.DateField(db_index=True) # INDEX: Crucial for date-based queries.
    sale_price = models.FloatField()
    
    animal = models.OneToOneField(Purchase, on_delete=models.CASCADE, related_name='sale')
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='sales')

    def __str__(self):
        return f'Sale of {self.animal.ear_tag} on {self.date}'

class Death(models.Model):
    """Represents the death event of an animal."""
    date = models.DateField(db_index=True) # INDEX: Crucial for date-based queries.
    cause = models.CharField(max_length=255, null=True, blank=True)
    
    animal = models.OneToOneField(Purchase, on_delete=models.CASCADE, related_name='death')
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='deaths')

    def __str__(self):
        return f'Death of {self.animal.ear_tag} on {self.date}'

class SanitaryProtocol(models.Model):
    """Represents a single sanitary protocol/health event for an animal."""
    date = models.DateField(db_index=True) # INDEX: Crucial for date-based queries.
    protocol_type = models.CharField(max_length=50)
    product_name = models.CharField(max_length=100, null=True, blank=True)
    dosage = models.CharField(max_length=50, null=True, blank=True)
    invoice_number = models.CharField(max_length=50, null=True, blank=True)
    
    animal = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name='protocols')
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='protocols')

    def __str__(self):
        return f'{self.protocol_type} for {self.animal.ear_tag}'

class LocationChange(models.Model):
    """Represents an animal moving from one location to another."""
    date = models.DateField(db_index=True) # INDEX: Crucial for date-based queries.
    
    animal = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name='location_changes')
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='location_changes')
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='change_events')
    sublocation = models.ForeignKey(Sublocation, on_delete=models.CASCADE, null=True, blank=True, related_name='change_events')

    def __str__(self):
        return f'{self.animal.ear_tag} moved to {self.location.name}'

class DietLog(models.Model):
    """Represents a single diet change event for an animal."""
    date = models.DateField(db_index=True) # INDEX: Crucial for date-based queries.
    diet_type = models.CharField(max_length=50)
    daily_intake_percentage = models.FloatField(null=True, blank=True)
    
    animal = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name='diet_logs')
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='diet_logs')

    def __str__(self):
        return f'Diet change for {self.animal.ear_tag} to {self.diet_type}'