from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('festival', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name='festival_festivalexpense'
                        AND column_name='payment_mode'
                    ) THEN
                        ALTER TABLE festival_festivalexpense
                        ADD COLUMN payment_mode varchar(20) NOT NULL DEFAULT 'Cash';
                    END IF;
                END$$;
            """,
            reverse_sql="SELECT 1;",
        ),
    ]
