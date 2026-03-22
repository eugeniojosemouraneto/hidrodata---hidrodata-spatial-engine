from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('ingestion', '0001_initial'), # Substitua pela sua última migration
    ]
    operations = [
        migrations.RunSQL(
            sql="CLUSTER ingestion_station USING ingestion_station_location_id;",
            reverse_sql="ALTER TABLE ingestion_station SET WITHOUT CLUSTER;"
        )
    ]