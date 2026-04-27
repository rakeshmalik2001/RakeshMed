from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0021_rolepermissionmatrix_matrix_permissions"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="approval_shift_weekdays",
            field=models.CharField(default="0,1,2,3,4,5,6", max_length=32),
        ),
    ]
