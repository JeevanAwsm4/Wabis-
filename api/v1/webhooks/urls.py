from django.contrib import admin
from django.urls import path
from api.v1.webhooks import views

urlpatterns = [
    path('sync-subscribers/', views.sync_subscribers, name='sync_subscribers'),
    path('registration-completed/', views.registration_completed, name='registration_completed'),
    path('form-sent/', views.form_sent, name='form_sent'),
    path('chat-with-human/', views.chat_with_human, name='chat_with_human'),

    path('whatsaap-reg-inbound/', views.whatsaap_reg_inbound, name='whatsaap_reg_inbound'),


    # Active subtypes
    path('giveaway-inbound/', views.active_giveaway, name='active_giveaway'),
    path('know-more/', views.active_know_more, name='active_know_more'),

    path('whatsaapnew-chat/', views.whatsaapnew_chat, name='whatsaapnew_chat'),


    path('image-url/',views.get_image_url, name='get_image_url'),
]




