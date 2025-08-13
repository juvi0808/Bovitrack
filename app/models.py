from app import db
from datetime import date, datetime

from . import db # Make sure db is imported

class Farm(db.Model):
    """Represents a single farm or property, acting as the top-level container for all other data."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    # --- Relationships ---
    # Defines the one-to-many link from a Farm to its associated records.
    # 'cascade="all, delete-orphan"' ensures that if a farm is deleted, all its related data is also deleted.
    locations = db.relationship('Location', backref='farm', lazy=True, cascade="all, delete-orphan")
    purchases = db.relationship('Purchase', backref='farm', lazy=True, cascade="all, delete-orphan")
    weightings = db.relationship('Weighting', backref='farm', lazy=True, cascade="all, delete-orphan")
    sales = db.relationship('Sale', backref='farm', lazy=True, cascade="all, delete-orphan")
    protocols = db.relationship('SanitaryProtocol', backref='farm', lazy=True, cascade="all, delete-orphan")
    location_changes = db.relationship('LocationChange', backref='farm', lazy=True, cascade="all, delete-orphan")
    diet_logs = db.relationship('DietLog', backref='farm', lazy=True, cascade="all, delete-orphan")
    deaths = db.relationship('Death', backref='farm', lazy=True, cascade="all, delete-orphan")
    sublocations = db.relationship('Sublocation', backref='farm', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        """Serializes the Farm object to a dictionary."""
        return {'id': self.id, 'name': self.name}

    def __repr__(self):
        """Provides a developer-friendly string representation of the object."""
        return f'<Farm {self.name}>'

class Location(db.Model):
    """
    Represents a physical location on a farm (e.g., pasture, feedlot).
    These locations can be assigned to animals or used for reporting.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    area_hectares = db.Column(db.Float, nullable=True) # Optional field for area
    grass_type = db.Column(db.String(50), nullable=True) # Optional field for grass type
    location_type = db.Column(db.String(50), nullable=True) # Optional field for type of location (e.g., pasture, feedlot)
    geo_json_data = db.Column(db.Text, nullable=True) # For future map use

    # --- Foreign Keys ---
    # Ensures location belongs to a specific farm.
    farm_id = db.Column(db.Integer, db.ForeignKey('farm.id'), nullable=False)

    # --- Relationships ---
    # This ensures that a location name is unique only within a specific farm.
    # No two locations on the same farm can have the same name.
    # We will add a relationship back to LocationChange later, but for now, we leave it simple.
    change_events = db.relationship('LocationChange', backref='location', lazy=True, cascade="all, delete-orphan")
    sublocations = db.relationship('Sublocation', backref='parent_location', lazy=True, cascade="all, delete-orphan")

    def to_dict(self):
        """Serializes the Location object to a dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'area_hectares': self.area_hectares,
            'grass_type': self.grass_type,
            'location_type': self.location_type,
            'farm_id': self.farm_id,
            'geo_json_data': self.geo_json_data,
            'sublocations': [sub.to_dict() for sub in self.sublocations],
        }

    def __repr__(self):
        """Provides a developer-friendly string representation of the object."""
        return f'<Location {self.name} (Farm: {self.farm_id})>'

class Sublocation(db.Model):
    """Represents a subdivision within a parent Location (e.g., a rotational paddock)."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    area_hectares = db.Column(db.Float, nullable=True) # The dedicated area column
    geo_json_data = db.Column(db.Text, nullable=True)

    # --- Foreign Keys ---
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=False)
    farm_id = db.Column(db.Integer, db.ForeignKey('farm.id'), nullable=False)

    # --- Relationships ---
    change_events = db.relationship('LocationChange', backref='sublocation', lazy=True)

    def to_dict(self):
        """Serializes the Sublocation object to a dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'area_hectares': self.area_hectares, # Added to the response
            'location_id': self.location_id,
            'geo_json_data': self.geo_json_data,
        }

    def __repr__(self):
        return f'<Sublocation {self.name} (Parent ID: {self.location_id})>'

class Purchase(db.Model):
    """Represents the entry record of a single animal into a farm."""
    id = db.Column(db.Integer, primary_key=True)
    ear_tag = db.Column(db.String(20), nullable=False)
    lot = db.Column(db.Integer, nullable=False)
    entry_date = db.Column(db.Date, nullable=False)
    entry_weight = db.Column(db.Float, nullable=False)
    sex = db.Column(db.String(1), nullable=False)
    entry_age = db.Column(db.Float, nullable=False)
    purchase_price = db.Column(db.Float, nullable=True) # Optional field
    race = db.Column(db.String(50), nullable=True)

    # --- Foreign Keys ---
    farm_id = db.Column(db.Integer, db.ForeignKey('farm.id'), nullable=False)

    # --- Relationships ---
    # One-to-many links to this animal's historical event records.
    # 'backref="animal"' allows an event (e.g., a Weighting object) to easily access its parent Purchase object via `weighting.animal`.
    weightings = db.relationship('Weighting', backref='animal', lazy=True, cascade="all, delete-orphan")
    protocols = db.relationship('SanitaryProtocol', backref='animal', lazy=True, cascade="all, delete-orphan")
    location_changes = db.relationship('LocationChange', backref='animal', lazy=True, cascade="all, delete-orphan")
    diet_logs = db.relationship('DietLog', backref='animal', lazy=True, cascade="all, delete-orphan")
    # One-to-one link to this animal's sale or death record.
    sale = db.relationship('Sale', backref='animal', lazy=True, uselist=False, cascade="all, delete-orphan")
    death = db.relationship('Death', backref='animal', lazy=True, uselist=False, cascade="all, delete-orphan")

    # --- Constraints ---
    # Ensures the combination of ear_tag and lot is unique within a farm.
    __table_args__ = (db.UniqueConstraint('ear_tag', 'lot', 'farm_id', name='_ear_tag_lot_farm_uc'),)

    def to_dict(self):
        """Serializes the Purchase object to a dictionary."""
        return {
            'id': self.id,
            'ear_tag': self.ear_tag,
            'lot': self.lot,
            'entry_date': self.entry_date.isoformat(),
            'entry_weight': self.entry_weight,
            'sex': self.sex,
            'entry_age': self.entry_age,
            'purchase_price': self.purchase_price,
            'race': self.race,
            'farm_id': self.farm_id
        }

    def calculate_kpis(self):
        """
        Calculates key performance indicators for this specific animal.
        Adjusts calculations based on whether the animal is sold.
        """
        today = date.today()
        kpis = {}

        # --- NEW: Add Current Location ---
        current_location_name = "N/A"
        current_location_id = None
        current_sublocation_name = None 
        current_sublocation_id = None   
        if self.location_changes:
            # Sort changes by date to find the most recent one
            latest_change = sorted(self.location_changes, key=lambda lc: lc.date, reverse=True)[0]
            current_location_name = latest_change.location.name
            current_location_id = latest_change.location.id
            if latest_change.sublocation: 
                current_sublocation_name = latest_change.sublocation.name
                current_sublocation_id = latest_change.sublocation.id
        
        current_diet_type = "N/A"
        current_diet_intake = None
        if self.diet_logs:
            # Sort changes by date to find the most recent one
            latest_diet = sorted(self.diet_logs, key=lambda lc: lc.date, reverse=True)[0]
            current_diet_type = latest_diet.diet_type
            current_diet_intake = latest_diet.daily_intake_percentage
        
        # --- GMD and Last Weight Calculation (works for both active and sold) ---
        sorted_weights = sorted(self.weightings, key=lambda w: w.date)
        gmd = 0.0
        last_weight = self.entry_weight
        last_weighting_date = self.entry_date

        if len(sorted_weights) > 1:
            # ... (the logic to calculate GMD is the same) ...
            first_weighting = sorted_weights[0] #row
            last_weighting = sorted_weights[-1] #row
            last_weight = last_weighting.weight_kg #weight
            last_weighting_date = last_weighting.date #date
            total_days = (last_weighting.date - first_weighting.date).days
            total_gain = last_weighting.weight_kg - first_weighting.weight_kg
            if total_days > 0:
                gmd = total_gain / total_days

        kpis['average_daily_gain_kg'] = round(gmd, 3)
        kpis['last_weight_kg'] = round(last_weight, 2)
        kpis['last_weighting_date'] = last_weighting_date.isoformat()

        # --- Status-Aware Calculations ---
        if self.is_sold:
            # For a sold animal, the "current" age is its age at the time of sale.
            days_on_farm = (self.sale.date - self.entry_date).days
            kpis['current_age_months'] = round(self.entry_age + (days_on_farm / 30.44), 2)
            # Forecasted weight is not applicable.
            kpis['forecasted_current_weight_kg'] = None
            kpis['status'] = 'Sold'
            kpis['days_on_farm'] = days_on_farm
        
        elif self.is_dead:
            days_on_farm = (self.death.date - self.entry_date).days
            kpis['current_age_months'] = round(self.entry_age + (days_on_farm / 30.44), 2)
            kpis['forecasted_current_weight_kg'] = None
            kpis['status'] = 'Dead'

        else:
            # For an active animal, calculate age and forecasted weight for today.
            days_on_farm = (today - self.entry_date).days
            kpis['current_age_months'] = round(self.entry_age + (days_on_farm / 30.44), 2)
            days_since_last_weight = (today - last_weighting_date).days
            forecasted_gain = days_since_last_weight * gmd
            kpis['forecasted_current_weight_kg'] = round(last_weight + forecasted_gain, 2)
            kpis['status'] = 'Active'
            kpis['days_on_farm'] = days_on_farm
            kpis['current_location_name'] = current_location_name        
            kpis['current_location_id'] = current_location_id
            kpis['current_sublocation_name'] = current_sublocation_name
            kpis['current_sublocation_id'] = current_sublocation_id
            kpis['current_diet_type'] = current_diet_type
            kpis['current_diet_intake'] = current_diet_intake
        

        return kpis
    
    @property
    def is_sold(self):
        """
        A simple property that checks if a sale record exists for this animal.
        Returns True if sold, False otherwise.
        The '@property' decorator lets us access it like an attribute (e.g., animal.is_sold)
        without needing parentheses.
        """
        return self.sale is not None
    
    @property
    def is_dead(self):
        """
        A simple property that checks if a sale record exists for this animal.
        Returns True if sold, False otherwise.
        The '@property' decorator lets us access it like an attribute (e.g., animal.is_sold)
        without needing parentheses.
        """
        return self.death is not None

    def __repr__(self):
        """Provides a developer-friendly string representation of the object."""
        return f'<Purchase {self.ear_tag}>'

class Weighting(db.Model):
    """Represents a single weight measurement event for an animal."""
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    weight_kg = db.Column(db.Float, nullable=False)

    # --- Foreign Keys ---
    animal_id = db.Column(db.Integer, db.ForeignKey('purchase.id'), nullable=False)
    farm_id = db.Column(db.Integer, db.ForeignKey('farm.id'), nullable=False)

    def to_dict(self):
        # This is a safe way to access the related animal's data.
        # If self.animal exists, we get its ear_tag. Otherwise, we return a default value like 'N/A' or None.
        ear_tag = self.animal.ear_tag if self.animal else 'Orphaned Record'
        lot = self.animal.lot if self.animal else 'N/A'
        
        return {
            'id': self.id,
            'date': self.date.isoformat(),
            'weight_kg': self.weight_kg,
            'animal_id': self.animal_id,
            'farm_id': self.farm_id,
            'ear_tag': ear_tag, # Use the safe variable
            'lot': lot          # Use the safe variable
        }

    def __repr__(self):
        """Provides a developer-friendly string representation of the object."""
        return f'<Weighting for animal {self.animal_id} on {self.date}>'

class Sale(db.Model):
    """Represents the sale event of an animal, marking its exit from the farm."""
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    sale_price = db.Column(db.Float, nullable=False)

    # --- Foreign Keys ---
    # 'unique=True' enforces that an animal can only be sold once.
    animal_id = db.Column(db.Integer, db.ForeignKey('purchase.id'), unique=True, nullable=False)
    farm_id = db.Column(db.Integer, db.ForeignKey('farm.id'), nullable=False)

    def to_dict(self):
        """
        Serializes the Sale object to a dictionary, now including all
        relevant KPIs calculated on the fly.
        """
        # --- Start of new, improved logic ---
        
        # 1. Get the final weight from the animal's weight history for accuracy.
        exit_weighting = Weighting.query.filter_by(animal_id=self.animal_id, date=self.date).first()
        exit_weight = exit_weighting.weight_kg if exit_weighting else 0.0

        # 2. Calculate all the KPIs right here.
        days_on_farm = (self.date - self.animal.entry_date).days
        total_gain = exit_weight - self.animal.entry_weight
        gmd_kg_day = (total_gain / days_on_farm) if days_on_farm > 0 and exit_weight > 0 else 0.0
        exit_age_months = self.animal.entry_age + (days_on_farm / 30.44)

        # --- End of new logic ---

        return {
            # Core data from the animal
            "animal_id": self.animal_id,
            "ear_tag": self.animal.ear_tag,
            "lot": self.animal.lot,
            "race": self.animal.race,
            "sex": self.animal.sex,
            
            # Core data from the sale itself
            "sale_id": self.id,
            "exit_date": self.date.isoformat(),
            "exit_price": self.sale_price,
            
            # Calculated KPIs
            "days_on_farm": days_on_farm,
            "exit_weight": exit_weight,
            "exit_age_months": round(exit_age_months, 2),
            "gmd_kg_day": round(gmd_kg_day, 3),

            # Historical data for context
            "entry_date": self.animal.entry_date.isoformat(),
            "entry_weight": self.animal.entry_weight,
            "entry_price": self.animal.purchase_price,
            
            # ID fields
            'farm_id': self.farm_id,
        }

    def __repr__(self):
        """Provides a developer-friendly string representation of the object."""
        return f'<Sale of animal {self.animal_id} on {self.date}>'

class SanitaryProtocol(db.Model):
    """Represents a single sanitary protocol/health event for an animal."""
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    protocol_type = db.Column(db.String(50), nullable=False)
    product_name = db.Column(db.String(100), nullable=True) # Optional
    dosage = db.Column(db.String(50), nullable=True) # Optional
    invoice_number = db.Column(db.String(50), nullable=True) # Optional 
    

    # --- Foreign Keys ---
    animal_id = db.Column(db.Integer, db.ForeignKey('purchase.id'), nullable=False)
    farm_id = db.Column(db.Integer, db.ForeignKey('farm.id'), nullable=False)

    def to_dict(self):
        """Serializes the SanitaryProtocol object to a dictionary."""
        return {
            "protocol_id": self.id,
            "date": self.date.isoformat(),
            "ear_tag": self.animal.ear_tag,
            "lot": self.animal.lot,
            "protocol_type": self.protocol_type,
            "product_name": self.product_name,
            "invoice_number": self.invoice_number,
            "dosage":self.dosage,
            "animal_id": self.animal_id,
            'farm_id': self.farm_id
        }



    def __repr__(self):
        """Provides a developer-friendly string representation of the object."""
        return f'<Protocol {self.protocol_type} for animal {self.animal_id}>'

class LocationChange(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)

    # --- Foreign Keys ---
    animal_id = db.Column(db.Integer, db.ForeignKey('purchase.id'), nullable=False)
    farm_id = db.Column(db.Integer, db.ForeignKey('farm.id'), nullable=False)

    # This now stores the ID of the structured Location, not a string name.
    # This creates a formal link to the Location table.
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=False)
    sublocation_id = db.Column(db.Integer, db.ForeignKey('sublocation.id'), nullable=True)

    def to_dict(self):
        """
        Serializes the LocationChange object to a dictionary, including
        the name of the linked location for convenience.
        """
        return {
            "location_change_id": self.id,
            "date": self.date.isoformat(),
            "ear_tag": self.animal.ear_tag,
            "lot": self.animal.lot,
            "location_name": self.location.name,
            "location_id": self.location.id,
            "animal_id": self.animal_id,
            'farm_id': self.farm_id
        }

    def __repr__(self):
        """Provides a developer-friendly string representation of the object."""
        # We can also improve the repr to show the location name.
        location_name = self.location.name if self.location else 'N/A'
        return f'<LocationChange for animal {self.animal_id} to {location_name}>'

class DietLog(db.Model):
    """Represents a single diet change event for an animal."""
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    diet_type = db.Column(db.String(50), nullable=False)
    daily_intake_percentage = db.Column(db.Float, nullable=True) # Optional field

    # --- Foreign Keys ---
    animal_id = db.Column(db.Integer, db.ForeignKey('purchase.id'), nullable=False)
    farm_id = db.Column(db.Integer, db.ForeignKey('farm.id'), nullable=False)

    def to_dict(self):
        """Serializes the DietLog object to a dictionary."""
        return {
            "diet_log_id": self.id,
            "date": self.date.isoformat(),
            "ear_tag": self.animal.ear_tag,
            "lot": self.animal.lot,
            "diet_type": self.diet_type,
            "daily_intake_percentage": self.daily_intake_percentage,
            "animal_id": self.animal_id,
            'farm_id': self.farm_id
        }

    def __repr__(self):
        """Provides a developer-friendly string representation of the object."""
        return f'<DietLog for animal {self.animal_id} on {self.date}>'
    
class Death(db.Model):
    """Represents the death event of an animal."""
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    cause = db.Column(db.String(255), nullable=True) # Optional field for cause of death

    # --- Foreign Keys ---
    # 'unique=True' enforces that an animal can only be recorded as dead once.
    animal_id = db.Column(db.Integer, db.ForeignKey('purchase.id'), unique=True, nullable=False)
    farm_id = db.Column(db.Integer, db.ForeignKey('farm.id'), nullable=False)

    def to_dict(self):
        """Serializes the Death object to a dictionary."""
        return {
            "death_id": self.id,
            "date": self.date.isoformat(),
            "ear_tag": self.animal.ear_tag,
            "lot": self.animal.lot,
            "cause": self.cause,
            "animal_id": self.animal_id,
            'farm_id': self.farm_id
        }

    def __repr__(self):
        """Provides a developer-friendly string representation of the object."""
        return f'<Death of animal {self.animal_id} on {self.date}>'