from django.contrib import admin
from . import models

# Register your models here to make them accessible in the admin interface.
admin.site.register(models.Farm)
admin.site.register(models.Location)
admin.site.register(models.Sublocation)
admin.site.register(models.Purchase)
admin.site.register(models.Weighting)
admin.site.register(models.Sale)
admin.site.register(models.Death)
admin.site.register(models.SanitaryProtocol)
admin.site.register(models.LocationChange)
admin.site.register(models.DietLog)