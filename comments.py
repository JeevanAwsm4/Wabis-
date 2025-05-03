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


# def generate_unique_code():
#     letters = ''.join(random.choices(string.ascii_uppercase, k=2))
#     numbers = ''.join(random.choices(string.digits, k=4))
#     return f'#{letters}{numbers}'