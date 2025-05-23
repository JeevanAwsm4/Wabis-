# Generated by Django 4.2.7 on 2025-04-29 08:57

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Subscriber',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('subscriber_id', models.BigIntegerField(unique=True)),
                ('chat_id', models.CharField(max_length=20)),
                ('first_name', models.CharField(max_length=100)),
                ('last_name', models.CharField(blank=True, max_length=100)),
                ('email', models.EmailField(blank=True, max_length=254, null=True)),
                ('gender', models.CharField(blank=True, max_length=20, null=True)),
                ('label_names', models.TextField(blank=True, null=True)),
            ],
        ),
    ]
