from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ('complaints', '0006_complaintattachment'),
    ]

    operations = [
        migrations.AddField(
            model_name='complaint',
            name='city_corporation',
            field=models.CharField(
                blank=True,
                choices=[
                    ('DNCC', 'Dhaka North City Corporation (DNCC)'),
                    ('DSCC', 'Dhaka South City Corporation (DSCC)'),
                ],
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='complaint',
            name='ward_number',
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                validators=[MinValueValidator(1), MaxValueValidator(75)],
            ),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='city_corporation',
            field=models.CharField(
                blank=True,
                choices=[
                    ('DNCC', 'Dhaka North City Corporation (DNCC)'),
                    ('DSCC', 'Dhaka South City Corporation (DSCC)'),
                ],
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='ward_number',
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                validators=[MinValueValidator(1), MaxValueValidator(75)],
            ),
        ),
        migrations.AddConstraint(
            model_name='userprofile',
            constraint=models.UniqueConstraint(
                condition=Q(
                    role='authority',
                    approval_status='approved',
                    ward_number__isnull=False,
                ) & ~Q(city_corporation=''),
                fields=('city_corporation', 'ward_number'),
                name='unique_approved_authority_per_service_ward',
            ),
        ),
    ]
