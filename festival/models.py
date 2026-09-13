import json
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User


FESTIVAL_TYPES = [
    ("Durga Puja", "Durga Puja"),
    ("Diwali", "Diwali"),
    ("Ganesh Chaturthi", "Ganesh Chaturthi"),
    ("Navratri", "Navratri"),
    ("Eid", "Eid"),
    ("Christmas", "Christmas"),
    ("Holi", "Holi"),
    ("Onam", "Onam"),
    ("Pongal", "Pongal"),
    ("Rath Yatra", "Rath Yatra"),
    ("Other", "Other"),
]

PAYMENT_CHOICES = [
    ("Cash", "Cash"),
    ("UPI", "UPI"),
    ("Bank Transfer", "Bank Transfer"),
    ("Cheque", "Cheque"),
    ("Card", "Card"),
]


class Festival(models.Model):
    """One festival event (e.g. Durga Puja 2025 – Ward 5)."""
    name = models.CharField(max_length=200)          # "Ward-5 Durga Puja 2025"
    festival_type = models.CharField(max_length=100, choices=FESTIVAL_TYPES, default="Other")
    location = models.CharField(max_length=300)       # Neighbourhood / puja pandal address
    start_date = models.DateField()
    end_date = models.DateField()
    target_collection = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def status(self):
        from datetime import date
        today = date.today()
        if self.start_date > today:
            return "Upcoming"
        if self.end_date >= today:
            return "Ongoing"
        return "Completed"

    @property
    def total_collected(self):
        return self.collections.aggregate(
            t=models.Sum("amount")
        )["t"] or Decimal("0")

    @property
    def total_expenses(self):
        return self.expenses.aggregate(
            t=models.Sum("amount")
        )["t"] or Decimal("0")

    @property
    def balance(self):
        return self.total_collected - self.total_expenses

    @property
    def upi_collected(self):
        return self.collections.filter(payment_mode="UPI").aggregate(
            t=models.Sum("amount")
        )["t"] or Decimal("0")

    @property
    def cash_collected(self):
        return self.collections.filter(payment_mode="Cash").aggregate(
            t=models.Sum("amount")
        )["t"] or Decimal("0")

    @property
    def upi_expenses(self):
        return self.expenses.filter(payment_mode="UPI").aggregate(
            t=models.Sum("amount")
        )["t"] or Decimal("0")

    @property
    def cash_expenses(self):
        return self.expenses.filter(payment_mode="Cash").aggregate(
            t=models.Sum("amount")
        )["t"] or Decimal("0")

    @property
    def upi_balance(self):
        return self.upi_collected - self.upi_expenses

    @property
    def cash_balance(self):
        return self.cash_collected - self.cash_expenses

    @property
    def collection_pct(self):
        if self.target_collection and self.target_collection > 0:
            return min(100, int(self.total_collected / self.target_collection * 100))
        return 0

    def __str__(self):
        return f"{self.name} ({self.festival_type})"


class ChandaMember(models.Model):
    """A person/household from whom chanda (donation) is expected."""
    festival = models.ForeignKey(Festival, on_delete=models.CASCADE, related_name="members")
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    promised_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                           help_text="Amount promised/expected from this member")
    notes = models.TextField(blank=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    @property
    def total_paid(self):
        return self.collections.aggregate(
            t=models.Sum("amount")
        )["t"] or Decimal("0")

    @property
    def pending_amount(self):
        return max(Decimal("0"), self.promised_amount - self.total_paid)

    @property
    def is_fully_paid(self):
        return self.total_paid >= self.promised_amount and self.promised_amount > 0

    def __str__(self):
        return f"{self.name} — {self.festival.name}"


class ChandaCollection(models.Model):
    """One chanda (donation) payment received from a member."""
    festival = models.ForeignKey(Festival, on_delete=models.CASCADE, related_name="collections")
    member = models.ForeignKey(ChandaMember, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name="collections",
                                help_text="Leave blank for walk-in / anonymous donors")
    donor_name = models.CharField(max_length=200, blank=True,
                                   help_text="Auto-filled from member; or enter manually for anonymous donor")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default="Cash")
    collected_by = models.CharField(max_length=100)
    date_collected = models.DateField()
    receipt_no = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_collected", "-created_at"]

    def save(self, *args, **kwargs):
        if self.member and not self.donor_name:
            self.donor_name = self.member.name
        super().save(*args, **kwargs)

    def __str__(self):
        return f"₹{self.amount} from {self.donor_name or 'Anonymous'} [{self.festival.name}]"


class FestivalExpense(models.Model):
    """Money spent on the festival."""
    festival = models.ForeignKey(Festival, on_delete=models.CASCADE, related_name="expenses")
    title = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_by = models.CharField(max_length=100)
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default="Cash")

    CATEGORY_CHOICES = [
        ("Decoration", "Decoration & Pandal"),
        ("Idol / Murti", "Idol / Murti"),
        ("Sound & Lighting", "Sound & Lighting"),
        ("Food & Prasad", "Food & Prasad"),
        ("Pooja Samagri", "Pooja Samagri"),
        ("Priest / Pundit", "Priest / Pundit"),
        ("Cultural Program", "Cultural Program"),
        ("Transport", "Transport & Logistics"),
        ("Printing", "Printing & Publicity"),
        ("Security", "Security & Barricading"),
        ("Miscellaneous", "Miscellaneous"),
    ]
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default="Miscellaneous")
    date = models.DateField()
    description = models.TextField(blank=True)
    receipt = models.ImageField(upload_to="receipts/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self):
        return f"{self.title} — ₹{self.amount} ({self.festival.name})"
