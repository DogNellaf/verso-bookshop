import decimal

import django.core.validators
import main.models
from decimal import Decimal
from django.db import migrations, models

# State rates on books, without local taxes (2025).
US_STATE_RATES = {
    "AL": "4",
    "AZ": "5.6",
    "AR": "6.5",
    "CA": "7.25",
    "CO": "2.9",
    "CT": "6.35",
    "DC": "6",
    "FL": "6",
    "GA": "4",
    "HI": "4",
    "ID": "6",
    "IL": "6.25",
    "IN": "7",
    "IA": "6",
    "KS": "6.5",
    "KY": "6",
    "LA": "5",
    "ME": "5.5",
    "MD": "6",
    "MA": "6.25",
    "MI": "6",
    "MN": "6.875",
    "MS": "7",
    "MO": "4.225",
    "NE": "5.5",
    "NV": "6.85",
    "NJ": "6.625",
    "NM": "4.875",
    "NY": "4",
    "NC": "4.75",
    "ND": "5",
    "OH": "5.75",
    "OK": "4.5",
    "PA": "6",
    "RI": "7",
    "SC": "6",
    "SD": "4.2",
    "TN": "7",
    "TX": "6.25",
    "UT": "4.85",
    "VT": "6",
    "VA": "4.3",
    "WA": "6.5",
    "WV": "6",
    "WI": "5",
    "WY": "4",
}

# Examples of combined state and local rates by ZIP prefix.
US_LOCAL_RATES = [
    ("NY", prefix, "8.875") for prefix in ("100", "101", "102", "103", "104", "112", "113", "114", "116")
] + [("IL", "606", "10.25")]

# (zone name, method code): (per extra kg, max weight in grams)
WEIGHT_PRICING = {
    ("United States", "standard"): ("1.50", 20000),
    ("United States", "express"): ("4.00", 10000),
    ("European Union", "standard"): ("2.00", 20000),
    ("European Union", "express"): ("5.00", 10000),
    ("Russia", "post"): ("1.50", 20000),
    ("Russia", "courier"): ("3.00", 15000),
    ("Rest of the world", "international"): ("6.00", 20000),
}


def move_tax_rates(apps, schema_editor):
    Old = apps.get_model("main", "TaxRate")
    New = apps.get_model("main", "RegionalTaxRate")
    for old in Old.objects.all():
        New.objects.create(country=old.country, rate=old.rate, name=old.name)
    for state, rate in US_STATE_RATES.items():
        New.objects.get_or_create(
            country="US", region=state, postal_prefix="",
            defaults={"rate": Decimal(rate), "name": "Sales tax"},
        )
    for state, prefix, rate in US_LOCAL_RATES:
        New.objects.get_or_create(
            country="US", region=state, postal_prefix=prefix,
            defaults={"rate": Decimal(rate), "name": "Sales tax"},
        )


def move_tax_rates_back(apps, schema_editor):
    Old = apps.get_model("main", "TaxRate")
    New = apps.get_model("main", "RegionalTaxRate")
    for new in New.objects.filter(region="", postal_prefix=""):
        Old.objects.create(country=new.country, rate=round(new.rate, 2), name=new.name)


def price_by_weight(apps, schema_editor):
    ShippingMethod = apps.get_model("main", "ShippingMethod")
    for method in ShippingMethod.objects.select_related("zone"):
        pricing = WEIGHT_PRICING.get((method.zone.name, method.code))
        if pricing:
            method.per_kg = Decimal(pricing[0])
            method.max_weight = pricing[1]
            method.save(update_fields=["per_kg", "max_weight"])


class Migration(migrations.Migration):
    dependencies = [
        ("main", "0013_partial_refunds"),
    ]

    operations = [
        migrations.AddField(
            model_name="book",
            name="weight",
            field=models.PositiveIntegerField(
                default=400,
                help_text="Shipping weight with packaging.",
                validators=[django.core.validators.MinValueValidator(1)],
                verbose_name="Weight (g)",
            ),
        ),
        migrations.AddField(
            model_name="shippingmethod",
            name="per_kg",
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal("0.00"),
                help_text="Added for every started kilogram above the first.",
                max_digits=8,
                validators=[django.core.validators.MinValueValidator(decimal.Decimal("0"))],
                verbose_name="Per extra kg (USD)",
            ),
        ),
        migrations.AddField(
            model_name="shippingmethod",
            name="max_weight",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Heavier orders can't use this method. Empty means no limit.",
                null=True,
                verbose_name="Max weight (g)",
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="shipping_weight",
            field=models.PositiveIntegerField(default=0, verbose_name="Weight (g)"),
        ),
        migrations.AddField(
            model_name="order",
            name="region",
            field=models.CharField(blank=True, max_length=100, verbose_name="State or region"),
        ),
        migrations.AlterField(
            model_name="order",
            name="tax_rate",
            field=models.DecimalField(
                decimal_places=3, default=Decimal("0.00"), max_digits=5, verbose_name="Tax rate, %"
            ),
        ),
        migrations.RunPython(price_by_weight, migrations.RunPython.noop),
        migrations.CreateModel(
            name="RegionalTaxRate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "country",
                    models.CharField(
                        max_length=2, validators=[main.models.validate_country], verbose_name="Country"
                    ),
                ),
                (
                    "region",
                    models.CharField(
                        blank=True,
                        help_text="State or province code, e.g. CA. Empty means the whole country.",
                        max_length=10,
                        verbose_name="Region",
                    ),
                ),
                (
                    "postal_prefix",
                    models.CharField(
                        blank=True,
                        help_text="Matches postal codes starting with it, e.g. 100 for Manhattan.",
                        max_length=10,
                        verbose_name="Postal code prefix",
                    ),
                ),
                (
                    "rate",
                    models.DecimalField(
                        decimal_places=3,
                        max_digits=5,
                        validators=[
                            django.core.validators.MinValueValidator(decimal.Decimal("0")),
                            django.core.validators.MaxValueValidator(100),
                        ],
                        verbose_name="Rate, %",
                    ),
                ),
                ("name", models.CharField(default="VAT", max_length=40, verbose_name="Name")),
                (
                    "tax_shipping",
                    models.BooleanField(
                        default=True, help_text="Apply the rate to shipping too.", verbose_name="Tax shipping"
                    ),
                ),
            ],
            options={
                "verbose_name": "Tax rate",
                "verbose_name_plural": "Tax rates",
                "ordering": ["country", "region", "postal_prefix"],
                "constraints": [
                    models.UniqueConstraint(
                        fields=("country", "region", "postal_prefix"), name="unique_tax_rate_scope"
                    )
                ],
            },
        ),
        migrations.RunPython(move_tax_rates, move_tax_rates_back),
        migrations.DeleteModel(name="TaxRate"),
        migrations.RenameModel(old_name="RegionalTaxRate", new_name="TaxRate"),
    ]
