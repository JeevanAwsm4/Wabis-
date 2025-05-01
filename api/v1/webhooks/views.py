import os
import requests
import json
import random
import string
from threading import Thread

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

GOOGLE_SCRIPT_URL = 'https://script.google.com/macros/s/AKfycbyQkj-Eu6O9vFIVaLUWJtXLwhw_yhAuWWp9vUV3D7bRy1rPmey2KxPN_ETbOCZMWaXW/exec'
API_TOKEN = '10283|zuHIJbEQ738v890ox6igIxz0rcjXxRl2tmNhuMC24c68c24a'
PHONE_NUMBER_ID = '646606975197281'

BATCH_SIZE = 1000  




def find_value_in_sheet(request):
    SEARCH_COLUMN = 2  # Column B
    SEARCH_VALUE = '919745158442'  # The value you are looking for
    
    # Get the absolute path of the credential file (adjust to match your structure)
    cred_path = "/etc/secrets/cred.json"  # Assuming 'cred.json' is at the root of your project

    # 1. Authenticate using the service account (gspread)
    gc = gspread.service_account(filename=cred_path)
    
    # 2. Open the spreadsheet and select the worksheet
    sh = gc.open("Fusfu - CQO 2025 Lead management MAIN")
    ws = sh.get_worksheet(0)  # Select the first worksheet

    # 3. Attempt to find the value in the given column
    cell = ws.find(SEARCH_VALUE, in_column=SEARCH_COLUMN)
    response = {
        'found': True,
        'value': SEARCH_VALUE,
        'row': cell.row,
        'column': cell.col
    }
    return JsonResponse(response)





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



def generate_unique_code():
    letters = ''.join(random.choices(string.ascii_uppercase, k=2))
    numbers = ''.join(random.choices(string.digits, k=4))
    return f'#{letters}{numbers}'


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

def update_subscriber_status(chat_id, status, lead_status):
    try:
        subscriber = Subscriber.objects.get(chat_id=chat_id)
        subscriber.status = status
        subscriber.lead_status = lead_status
        subscriber.save()
        send_to_google_sheet(subscriber)  
        return True
    except Subscriber.DoesNotExist:
        return False

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
@require_POST
# def registration_completed(request):
#     print("[STEP 1] Incoming request...")

#     try:
#         body = json.loads(request.body)
#         print("[STEP 2] Request body parsed:", body)

#         name = body.get('student-name')
#         chat_id = body.get('chat_id')
#         email = body.get('student-email')
#         phone = body.get('student-mobile') or chat_id

#         print(f"[STEP 3] Extracted chat_id: {chat_id}, email: {email}, phone: {phone}, name: {name}")

#         if not chat_id:
#             print("[ERROR] chat_id missing")
#             return JsonResponse({'success': False, 'error': 'Invalid chat_id'}, status=400)

#         try:
#             subscriber = Subscriber.objects.get(chat_id=chat_id)
#             print(f"[STEP 4] Subscriber found: {subscriber}")
#         except Subscriber.DoesNotExist:
#             print("[ERROR] Subscriber not found")
#             return JsonResponse({'success': False, 'error': 'Subscriber not found'}, status=404)

#         if not subscriber.unique_code:
#             print("[STEP 5] Generating new unique_code...")
#             subscriber.unique_code = generate_unique_code()
#             subscriber.save()
#             print(f"[STEP 6] Unique code saved: {subscriber.unique_code}")

#         updated = update_subscriber_status(chat_id, 'REGESTERED', 'registered')
#         print(f"[STEP 7] Subscriber status update result: {updated}")

#         if updated:
#             send_to_google_sheet(subscriber)
#             print("[STEP 8] Sent to Google Sheet")

#             generate_and_send_image(
#                 name=subscriber.first_name,
#                 reg_id=subscriber.unique_code,
#                 phone=phone,
#                 email=email
#             )
#             print("[STEP 9] Image generated")

#             image_filename = f"output_{subscriber.unique_code}.jpg"
#             image_path = os.path.join("assets/user", image_filename)
#             print(f"[STEP 10] Image path: {image_path}")

#             if not os.path.exists(image_path):
#                 print("[ERROR] Image file not found")
#                 return JsonResponse({'success': False, 'error': 'Image file not found'}, status=404)

#             encoded_filename = quote(image_filename)
#             scheme = 'https' if request.is_secure() else 'http'
#             domain = request.get_host()
#             image_url = f"{scheme}://{domain}/assets/user/{encoded_filename}"
#             print(f"[STEP 11] Image URL generated: {image_url}")
#             webhook_url = "https://bot.wabis.in/webhook/whatsapp-workflow/136743.143544.173675.1746087689"
#             payload = {
#                 "studentNameWbh": name,
#                 "studentRegId": subscriber.unique_code,
#                 "studentEmailWbh": email,
#                 "studentPhoneWbh": phone,
#                 "IMAGE": image_url
#             }

#             print(f"[STEP 12] Sending payload to Wabis: {payload}")
#             try:
#                 response = requests.post(webhook_url, json=payload, timeout=5)
#                 print(f"[STEP 13] Wabis webhook response: {response.status_code}, {response.text}")
#             except Exception as e:
#                 print(f"[ERROR] Failed to send to Wabis webhook: {e}")

#             print("[STEP 14] All operations completed successfully.")
#             return JsonResponse({'success': True})

#         print("[ERROR] Failed to update subscriber status")
#         return JsonResponse({'success': False, 'error': 'Failed to update status'}, status=400)

#     except json.JSONDecodeError as e:
#         print("[ERROR] JSON decode failed:", e)
#         return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

#     except Exception as e:
#         import traceback
#         print("[ERROR] Unexpected error occurred:")
#         traceback.print_exc()
#         return JsonResponse({'success': False, 'error': str(e)}, status=500)
def registration_completed(request):
    print("[STEP 1] Incoming request...")

    try:
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

        updated = update_subscriber_status(chat_id, 'REGESTERED', 'registered')
        print(f"[STEP 7] Subscriber status update result: {updated}")

        if updated:
            send_to_google_sheet(subscriber)
            print("[STEP 8] Sent to Google Sheet")

            # generate_and_send_image(
            #     name=subscriber.first_name,
            #     reg_id=subscriber.unique_code,
            #     phone=phone,
            #     email=email
            # )
            # print("[STEP 9] Image generated")

            # image_filename = f"output_{subscriber.unique_code}.jpg"
            # image_path = os.path.join("assets/user", image_filename)
            # print(f"[STEP 10] Image path: {image_path}")

            # if not os.path.exists(image_path):
            #     print("[ERROR] Image file not found")
            #     return JsonResponse({'success': False, 'error': 'Image file not found'}, status=404)

            # encoded_filename = quote(image_filename)
            # scheme = 'https' if request.is_secure() else 'http'
            # domain = request.get_host()
            # image_url = f"{scheme}://{domain}/assets/user/{encoded_filename}"
            # print(f"[STEP 11] Image URL generated: {image_url}")
            webhook_url = "https://bot.wabis.in/webhook/whatsapp-workflow/136743.143544.173675.1746087689"
            payload = {
                "studentNameWbh": name,
                "studentRegId": subscriber.unique_code,
                "studentEmailWbh": email,
                "studentPhoneWbh": phone,
            }

            print(f"[STEP 12] Sending payload to Wabis: {payload}")
            try:
                response = requests.post(webhook_url, json=payload, timeout=5)
                print(f"[STEP 13] Wabis webhook response: {response.status_code}, {response.text}")
            except Exception as e:
                print(f"[ERROR] Failed to send to Wabis webhook: {e}")

            print("[STEP 14] All operations completed successfully.")
            return JsonResponse({'success': True})

        print("[ERROR] Failed to update subscriber status")
        return JsonResponse({'success': False, 'error': 'Failed to update status'}, status=400)

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
    print('NEWWWWW ',request)
    chat_id = extract_chat_id(request)
    if chat_id and update_subscriber_status(chat_id, 'FORM SENT', 'active'):
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Subscriber not found or invalid payload'}, status=404)

@csrf_exempt
@require_POST
def active_giveaway(request):
    print('NEWWWWW -active_giveaway',request)
    chat_id = extract_chat_id(request)
    if chat_id and update_subscriber_status(chat_id, 'FORM SENT', 'active'):
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Subscriber not found or invalid payload'}, status=404)

@csrf_exempt
@require_POST
def whatsaap_reg_inbound(request):
    print('NEWWWWW whatsaap_reg_inbound',request)
    chat_id = extract_chat_id(request)
    if chat_id and update_subscriber_status(chat_id, 'FORM SENT', 'active'):
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Subscriber not found or invalid payload'}, status=404)

@csrf_exempt
@require_POST
def active_know_more(request):
    print('NEWWWWW active_know_more',request)
    chat_id = extract_chat_id(request)
    if chat_id :
        Thread(target=update_subscriber_status, args=(chat_id, 'OPEN', 'open')).start()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Subscriber not found or invalid payload'}, status=404)

@csrf_exempt
@require_POST
def chat_with_human(request):
    print('NEWWWWW chat_with_human',request)
    chat_id = extract_chat_id(request)
    if chat_id and update_subscriber_status(chat_id, 'CHAT WITH HUMAN', 'open'):
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
