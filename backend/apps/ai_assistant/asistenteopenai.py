import os
from django.conf import settings
from openai import OpenAI

ASSISTANT_ID = settings.OPENAI_ASSISTANT_ID
client = OpenAI(api_key=settings.OPENAI_API_KEY)

thread = client.beta.threads.create()
thread_message = client.beta.threads.messages.create(
    thread_id=thread.id,
    role='user',
    content='Hola, ¿cómo estás?'
)
thread_messages = client.beta.threads.messages.list(
    thread_id=thread.id,
)
for message in thread_messages:
    print(message.content[0].text.value)
run = client.beta.threads.runs.create(
    thread_id=thread.id,
    assistant_id=ASSISTANT_ID,
)
print(run.id)


    