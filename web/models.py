# models.py

from django.db import models

class Subscriber(models.Model):
    unique_code = models.CharField(max_length=7, unique=True, blank=True, null=True)
    subscriber_id = models.BigIntegerField(unique=True)
    chat_id = models.CharField(max_length=20)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(null=True, blank=True)
    gender = models.CharField(max_length=20, null=True, blank=True)
    label_names = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=100, blank=True, null=True)
    lead_status = models.CharField(max_length=100, blank=True, null=True)


    def __str__(self):
        return f"{self.first_name} ({self.chat_id})"

class SerialTracker(models.Model):
    prefix = models.CharField(max_length=2, default='AA')
    last_number = models.IntegerField(default=0)