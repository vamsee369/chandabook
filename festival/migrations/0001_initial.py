from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Festival",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200)),
                ("festival_type", models.CharField(choices=[("Durga Puja","Durga Puja"),("Diwali","Diwali"),("Ganesh Chaturthi","Ganesh Chaturthi"),("Navratri","Navratri"),("Eid","Eid"),("Christmas","Christmas"),("Holi","Holi"),("Onam","Onam"),("Pongal","Pongal"),("Rath Yatra","Rath Yatra"),("Other","Other")], default="Other", max_length=100)),
                ("location", models.CharField(max_length=300)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField()),
                ("target_collection", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("description", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ChandaMember",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200)),
                ("phone", models.CharField(blank=True, max_length=15)),
                ("address", models.TextField(blank=True)),
                ("promised_amount", models.DecimalField(decimal_places=2, default=0, help_text="Amount promised/expected from this member", max_digits=10)),
                ("notes", models.TextField(blank=True)),
                ("added_at", models.DateTimeField(auto_now_add=True)),
                ("festival", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="members", to="festival.festival")),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="ChandaCollection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("donor_name", models.CharField(blank=True, help_text="Auto-filled from member; or enter manually for anonymous donor", max_length=200)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("payment_mode", models.CharField(choices=[("Cash","Cash"),("UPI","UPI"),("Bank Transfer","Bank Transfer"),("Cheque","Cheque"),("Card","Card")], default="Cash", max_length=20)),
                ("collected_by", models.CharField(max_length=100)),
                ("date_collected", models.DateField()),
                ("receipt_no", models.CharField(blank=True, max_length=50)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("festival", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="collections", to="festival.festival")),
                ("member", models.ForeignKey(blank=True, help_text="Leave blank for walk-in / anonymous donors", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="collections", to="festival.chandamember")),
            ],
            options={"ordering": ["-date_collected", "-created_at"]},
        ),
        migrations.CreateModel(
            name="FestivalExpense",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                ("paid_by", models.CharField(max_length=100)),
                ("payment_mode", models.CharField(choices=[("Cash","Cash"),("UPI","UPI"),("Bank Transfer","Bank Transfer"),("Cheque","Cheque"),("Card","Card")], default="Cash", max_length=20)),
                ("category", models.CharField(choices=[("Decoration","Decoration & Pandal"),("Idol / Murti","Idol / Murti"),("Sound & Lighting","Sound & Lighting"),("Food & Prasad","Food & Prasad"),("Pooja Samagri","Pooja Samagri"),("Priest / Pundit","Priest / Pundit"),("Cultural Program","Cultural Program"),("Transport","Transport & Logistics"),("Printing","Printing & Publicity"),("Security","Security & Barricading"),("Miscellaneous","Miscellaneous")], default="Miscellaneous", max_length=50)),
                ("date", models.DateField()),
                ("description", models.TextField(blank=True)),
                ("receipt", models.ImageField(blank=True, null=True, upload_to="receipts/")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("festival", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="expenses", to="festival.festival")),
            ],
            options={"ordering": ["-date", "-created_at"]},
        ),
    ]
