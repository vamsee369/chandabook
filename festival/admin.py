from django.contrib import admin
from .models import Festival, ChandaMember, ChandaCollection, FestivalExpense


@admin.register(Festival)
class FestivalAdmin(admin.ModelAdmin):
    list_display = ["name", "festival_type", "location", "start_date", "end_date", "target_collection", "created_by"]
    list_filter = ["festival_type", "start_date"]
    search_fields = ["name", "location"]


@admin.register(ChandaMember)
class ChandaMemberAdmin(admin.ModelAdmin):
    list_display = ["name", "festival", "phone", "promised_amount", "total_paid"]
    list_filter = ["festival"]
    search_fields = ["name", "phone"]

    def total_paid(self, obj):
        return obj.total_paid
    total_paid.short_description = "Paid"


@admin.register(ChandaCollection)
class ChandaCollectionAdmin(admin.ModelAdmin):
    list_display = ["donor_name", "festival", "amount", "payment_mode", "collected_by", "date_collected", "receipt_no"]
    list_filter = ["festival", "payment_mode", "date_collected"]
    search_fields = ["donor_name", "collected_by", "receipt_no"]


@admin.register(FestivalExpense)
class FestivalExpenseAdmin(admin.ModelAdmin):
    list_display = ["title", "festival", "category", "amount", "paid_by", "payment_mode", "date"]
    list_filter = ["festival", "category", "payment_mode"]
    search_fields = ["title", "paid_by"]
