from django.urls import path
from . import views

urlpatterns = [
    path(
        'checkout/<int:course_pk>/',
        views.initiate_payment,
        name='initiate_payment',
    ),
    path(
        'success/<int:payment_id>/',
        views.payment_success,
        name='payment_success',
    ),
    path(
        'webhook/paymob/',
        views.paymob_webhook,
        name='paymob_webhook',
    ),
]