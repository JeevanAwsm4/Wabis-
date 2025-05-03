import os
import requests
import json
import random
import string
from threading import Thread
import base64
from web.models import SerialTracker

from more_itertools import chunked
from urllib.parse import quote
from PIL import Image, ImageDraw, ImageFont

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.views.decorators.http import require_POST
import gspread
from django.http import JsonResponse
from django.conf import settings
from web.models import Subscriber
from django.http import HttpResponse
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import AuthorizedSession


load_dotenv()
GOOGLE_SCRIPT_URL = os.getenv('GOOGLE_SCRIPT_URL')
API_TOKEN = os.getenv('API_TOKEN')
PHONE_NUMBER_ID = os.getenv('PHONE_NUMBER_ID')
# print(API_TOKEN)

BATCH_SIZE = 1000 


b64 = os.getenv("SERVICE_CREDS_B64")
creds_dict = json.loads(base64.b64decode(b64))
# print(creds_dict)


scopes = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Create Credentials object
creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)

# Authorize a gspread client with these credentials
gc = gspread.Client(auth=creds)
gc.session = AuthorizedSession(creds)  # ensure HTTP client is set


sh = gc.open("Fusfu - CQO 2025 Lead management MAIN")
data_main = sh.get_worksheet(0) 



def send_to_google_sheet(subscriber):
    payload = {
        "subscriber_id": subscriber.subscriber_id,
        "chat_id": subscriber.chat_id,
        "first_name": subscriber.first_name,
        "status": subscriber.status,
        "lead_status": subscriber.lead_status,
        "unique_code": subscriber.unique_code  
    }
    try:
        response = requests.post(GOOGLE_SCRIPT_URL, json=payload, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"[Google Sheet Sync] Failed for {subscriber.subscriber_id}: {e}")


def sheet_update_or_append(request,cid,leadstatus,whatsappstatus,source=None):
    body = json.loads(request.body) 
    cell = data_main.find(cid, in_column=2)
    if cell != None :
        data_main.update_cell(cell.row, 7, leadstatus)
        data_main.update_cell(cell.row, 8, whatsappstatus)
        if source != None :
            data_main.update_cell(cell.row, 5, source)
    else:
        data_main.append_row( ['----',cid,body.get('first_name'),'',source,'',leadstatus,whatsappstatus])


def newchatfunct(request,cid,):
    body = json.loads(request.body) 
    cell = data_main.find(cid, in_column=2)
    if cell == None :
        data_main.append_row( ['----',cid,body.get('first_name'),'','WhatsApp New','','New','NOT MESSAGED'])



def generate_unique_code():
    with transaction.atomic():
        tracker, created = SerialTracker.objects.select_for_update().get_or_create(pk=1)
        
        tracker.last_number += 1
        tracker.save()

        return f"#{tracker.prefix}{tracker.last_number:04d}"  # E.g., #AA0001
def generate_and_send_image(name, reg_id, phone, email, output_path=None):
    if output_path is None:
        output_path = f'assets/user/output_{reg_id}.jpg'

    img = Image.open("assets/template.jpg")  

    draw = ImageDraw.Draw(img)

    font = ImageFont.load_default()

    draw.text((105, 182), f"{name}", fill="black", font=font)
    draw.text((225,353), f"{reg_id}", fill="black", font=font)
    draw.text((225, 417), f"{phone}", fill="black", font=font)
    draw.text((225, 480), f"{email}", fill="blue", font=font)

    img.save(output_path)
    return output_path


def thread_update_subscriber_status(chat_id, status, lead_status):
    try:
        subscriber = Subscriber.objects.get(chat_id=chat_id)
        subscriber.status = status
        subscriber.lead_status = lead_status
        subscriber.save()
        send_to_google_sheet(subscriber)  
        return True
    except Subscriber.DoesNotExist:
        return False

def update_subscriber_status(chat_id, status, lead_status):
        Thread(target=thread_update_subscriber_status, args=(chat_id,status, lead_status)).start()


def extract_chat_id(request):
    try:
        body = json.loads(request.body)
        return body.get('chat_id')
    except json.JSONDecodeError:
        return None

@csrf_exempt
def sync_subscribers(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)

    url = "https://bot.wabis.in/api/v1/whatsapp/subscriber/list"
    params = {
        'apiToken': API_TOKEN,
        'phone_number_id': PHONE_NUMBER_ID,
        'limit': 2000000,
        'offset': 1
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        return JsonResponse({'status_code': 500, 'error': 'Failed to fetch from Wabis'}, status=500)

    data = response.json().get('message', [])
    subscribers_to_create = []
    subscribers_list = [] 

    for item in data:
        subscriber = Subscriber(
            subscriber_id=item['subscriber_id'],
            chat_id=item.get('chat_id'),
            first_name=item.get('first_name', ''),
            last_name=item.get('last_name', ''),
            email=item.get('email'),
            gender=item.get('gender'),
            label_names=item.get('label_names')
        )
        subscribers_to_create.append(subscriber)
        subscribers_list.append({
            'subscriber_id': item['subscriber_id'],
            'chat_id': item.get('chat_id'),
            'first_name': item.get('first_name', ''),
            'last_name': item.get('last_name', ''),
            'email': item.get('email'),
            'gender': item.get('gender'),
            'label_names': item.get('label_names')
        })

    synced = 0

    with transaction.atomic():
        for batch in chunked(subscribers_to_create, BATCH_SIZE):
            Subscriber.objects.bulk_create(
                batch,
                batch_size=BATCH_SIZE,
                ignore_conflicts=True 
            )
            synced += len(batch)

    return JsonResponse({
        'status_code': 200,
        'message': f'Successfully synced {synced} subscribers',
        'count': synced,
        'subscribers': subscribers_list  
    })

@csrf_exempt
def welcome_view(request):
    return HttpResponse("<h1>Welcome to fpwebhook site</h1>")


@csrf_exempt
def testuniwuenumb(request):
    uq = generate_unique_code()

    return JsonResponse({'uq': uq})


@csrf_exempt
@require_POST
def regproxess(request):


            body = json.loads(request.body)
            print("[STEP 2] Request body parsed:", body)

            name = body.get('student-name')
            chat_id = body.get('chat_id')
            email = body.get('student-email')
            phone = body.get('student-mobile') or chat_id

            print(f"[STEP 3] Extracted chat_id: {chat_id}, email: {email}, phone: {phone}, name: {name}")

            if not chat_id:
                print("[ERROR] chat_id missing")
                return JsonResponse({'success': False, 'error': 'Invalid chat_id'}, status=400)

            try:
                subscriber = Subscriber.objects.get(chat_id=chat_id)
                print(f"[STEP 4] Subscriber found: {subscriber}")
            except Subscriber.DoesNotExist:
                print("[ERROR] Subscriber not found")
                return JsonResponse({'success': False, 'error': 'Subscriber not found'}, status=404)

            if not subscriber.unique_code:
                print("[STEP 5] Generating new unique_code...")
                subscriber.unique_code = generate_unique_code()
                subscriber.save()
                print(f"[STEP 6] Unique code saved: {subscriber.unique_code}")

            

            lead_status = 'registered'
            whatsappstatus ='REGISTERED'
            cell = data_main.find(chat_id, in_column=2)
            if cell != None :
                data_main.update_cell(cell.row, 7, lead_status)
                data_main.update_cell(cell.row, 8, whatsappstatus)
                data_main.update_cell(cell.row, 12, subscriber.unique_code)
            else:
                data_main.append_row( ['----',chat_id,body.get('first_name'),'',source,'',leadstatus,whatsappstatus,"","","",subscriber.unique_code])

            webhook_url = "https://bot.wabis.in/webhook/whatsapp-workflow/136743.143544.173675.1746126129"
            payload = {
                "studentNameWbh": name,
                "studentRegId": subscriber.unique_code,
                "studentEmailWbh": email,
                "studentPhoneWbh": phone,
                "chat_id": chat_id
            }

            print(f"[STEP 12] Sending payload to Wabis: {payload}")
            try:
                response = requests.post(webhook_url, json=payload, timeout=5)
                print(f"[STEP 13] Wabis webhook response: {response.status_code}, {response.text}")
            except Exception as e:
                print(f"[ERROR] Failed to send to Wabis webhook: {e}")

            print("[STEP 14] All operations completed successfully.")

@csrf_exempt
@require_POST
def registration_completed(request):
    print("[STEP 1] Incoming request...")

    try:
        Thread(target=regproxess, args=(request,)).start()

        return JsonResponse({'success': True})

          
    except json.JSONDecodeError as e:
        print("[ERROR] JSON decode failed:", e)
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    except Exception as e:
        import traceback
        print("[ERROR] Unexpected error occurred:")
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
@require_POST
def form_sent(request):
    print('form sent ',request)
    chat_id = extract_chat_id(request)
    if chat_id :
        # update_subscriber_status(chat_id, 'FORM SENT', 'active')
        lead_status = 'active'
        whatsappstatus ='FORM SENT'
        Thread(target=sheet_update_or_append, args=(request,chat_id, lead_status,whatsappstatus)).start()

        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Subscriber not found or invalid payload'}, status=404)

@csrf_exempt
@require_POST
def active_giveaway(request):
    print('giveaway',request)
    chat_id = extract_chat_id(request)
    if chat_id :
        lead_status = 'active'
        whatsappstatus ='FORM SENT'
        Thread(target=sheet_update_or_append, args=(request,chat_id, lead_status,whatsappstatus,"GiveAway")).start()

        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Subscriber not found or invalid payload'}, status=404)

@csrf_exempt
@require_POST
def whatsaap_reg_inbound(request):
    print('whatsaap_reg_inbound',request)
    chat_id = extract_chat_id(request)
    if chat_id :
        lead_status = 'active'
        whatsappstatus ='FORM SENT'
        Thread(target=sheet_update_or_append, args=(request,chat_id, lead_status,whatsappstatus,"WhatsApp inbound")).start()

        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Subscriber not found or invalid payload'}, status=404)

@csrf_exempt
@require_POST
def active_know_more(request):
    print('active_know_more',request)
    chat_id = extract_chat_id(request)
    if chat_id :
        # update_subscriber_status(chat_id, 'OPEN', 'open')
        lead_status = 'open'
        whatsappstatus ='OPEN'
        Thread(target=sheet_update_or_append, args=(request,chat_id, lead_status,whatsappstatus)).start()

        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Subscriber not found or invalid payload'}, status=404)

@csrf_exempt
@require_POST
def chat_with_human(request):
    print(' chat_with_human',request)
    chat_id = extract_chat_id(request)
    if chat_id :
        # update_subscriber_status(chat_id, '', 'open')
        lead_status = 'open'
        whatsappstatus ='CHAT WITH HUMAN'
        Thread(target=sheet_update_or_append, args=(request,chat_id, lead_status,whatsappstatus)).start()

        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Subscriber not found or invalid payload'}, status=404)


@csrf_exempt
@require_POST

def whatsaapnew_chat (request):
    print(' chat_with_human',request)
    chat_id = extract_chat_id(request)
    if chat_id :
        Thread(target=newchatfunct, args=(request,chat_id)).start()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Subscriber not found or invalid payload'}, status=404)


@csrf_exempt
@require_POST



def get_image_url(request):
    try:
        chat_id = extract_chat_id(request)

        if not chat_id:
            return JsonResponse({'success': False, 'error': 'Missing subscriber_id'}, status=400)

        subscriber = Subscriber.objects.get(chat_id=chat_id)

        if not subscriber.unique_code:
            return JsonResponse({'success': False, 'error': 'Image not available (no unique code)'}, status=404)

        image_filename = f"output_{subscriber.unique_code}.jpg"
        image_path = os.path.join("assets/user", image_filename)

        if not os.path.exists(image_path):
            return JsonResponse({'success': False, 'error': 'Image file not found'}, status=404)

        encoded_filename = quote(image_filename)

        scheme = 'https' if request.is_secure() else 'http'
        domain = request.get_host()
        image_url = f"{scheme}://{domain}/assets/user/{encoded_filename}"

        return JsonResponse({'success': True, 'image_url': image_url})

    except Subscriber.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Subscriber not found'}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
