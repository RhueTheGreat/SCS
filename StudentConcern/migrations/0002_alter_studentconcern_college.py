from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('StudentConcern', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='studentconcern',
            name='College',
            field=models.CharField(choices=[('College of Computer Studies', 'College of Computer Studies'), ('College of Education', 'College of Education'), ('College of Agriculture', 'College of Agriculture')], max_length=100),
        ),
    ]
