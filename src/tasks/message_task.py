from src.config.celery import celery_app
from typing import Optional
from confluent_kafka import Producer
import json
from src.config.settings import settings
from confluent_kafka import Consumer
import time
from src.config.database import engine
from sqlmodel import Session
from celery.schedules import crontab

# Import models from centralized location to avoid circular imports
from src.models import Message, Conversation


@celery_app.task
def save_messages(conversation_id: int, data:dict,user_id:Optional[int]=None):
    try:
        print(f"saving message in queue for conversation_id: {conversation_id}")
        
        # Debug: Check if there are any conversations in the database
        all_conversations = Conversation.get_all()
        print(f"Total conversations in database: {len(all_conversations)}")
        if all_conversations:
            print(f"Available conversation IDs: {[c.id for c in all_conversations]}")
        
        conversation = Conversation.get(conversation_id)

        if not conversation:
            print(f"Conversation with ID {conversation_id} not found")
            return

        customer_id = conversation.customer_id
        print(f"Found conversation: {conversation.id}, customer_id: {customer_id}")

        if user_id:
            customer_id = None

        # Kafka producer logic
        producer = Producer({'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS})
        kafka_payload = {
            'conversation_id': conversation_id,
            'user_id': user_id,
            'message': data.get('message')
        }
        producer.produce(settings.KAFKA_TOPIC, json.dumps(kafka_payload).encode('utf-8'))
        producer.flush()
        print("Message sent to Kafka successfully")
    except Exception as e:
        print(f"kafka error producer {e}")
        import traceback
        traceback.print_exc()
    





    
def run_kafka_consumer_batch(
    batch_size: int = 20,
    poll_timeout: float = 1.0,
    flush_interval: float = 5.0
):
    """
    Run a Kafka consumer that batches messages and bulk inserts them into the database.
    :param batch_size: Number of messages per batch insert
    :param poll_timeout: Kafka poll timeout in seconds
    :param flush_interval: Max seconds to wait before flushing batch
    """
    print("start kafka consumer ")
    consumer = Consumer({
        'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
        'group.id': 'chatboq-message-batch-consumer',
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': True
    })


    consumer.subscribe([settings.KAFKA_TOPIC])

    batch = []
    last_flush = time.time()
    print("Kafka batch consumer started...")
    try:
        while True:
            msg = consumer.poll(poll_timeout)
            print(f'messages  {msg}')
            now = time.time()
            if msg is not None and not msg.error():
                data = json.loads(msg.value().decode('utf-8'))
                batch.append(data)
            # Flush if batch size or interval reached
            # if len(batch) >= batch_size or (batch and now - last_flush >= flush_interval):
            #     with Session(engine) as session:
            #         objs = [
            #             Message(
            #                 conversation_id=m['conversation_id'],
            #                 content=m['message'],
            #                 customer_id=None,  # Set if available in payload
            #                 user_id=m.get('user_id')
            #             ) for m in batch
            #         ]
            #         session.add_all(objs)
            #         session.commit()
            #     print(f"Inserted batch of {len(batch)} messages.")
            #     batch.clear()
            #     last_flush = now
    except KeyboardInterrupt:
        print("Kafka batch consumer stopped.")
    finally:
        consumer.close()
    





    
# Periodic task to consume Kafka messages in batch every 10 seconds (adjust as needed)
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    
    sender.add_periodic_task(10.0, consume_kafka_messages_batch.s(), name='consume kafka messages every 10s')

@celery_app.task
def consume_kafka_messages_batch(batch_size: int = 20, poll_timeout: float = 1.0, max_polls: int = 10):
    """
    Celery task to consume a batch of messages from Kafka and insert them into the DB.
    :param batch_size: Number of messages per DB insert
    :param poll_timeout: Kafka poll timeout in seconds
    :param max_polls: How many times to poll Kafka per run
    """
    print("save messages in batch ")
    consumer = Consumer({
        'bootstrap.servers': settings.KAFKA_BOOTSTRAP_SERVERS,
        'group.id': 'chatboq-message-batch-consumer',
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': True
    })

    consumer.subscribe([settings.KAFKA_TOPIC])
    

    batch = []
    try:
        for _ in range(max_polls):
            msg = consumer.poll(poll_timeout)
            if msg is not None and not msg.error():
                data = json.loads(msg.value().decode('utf-8'))
                batch.append(data)
            if len(batch) >= batch_size:
                break
        if batch:
            with Session(engine) as session:
                objs = [
                    Message(
                        conversation_id=m['conversation_id'],
                        content=m['message'],
                        customer_id=None,  # Set if available in payload
                        user_id=m.get('user_id')
                    ) for m in batch
                ]
                session.add_all(objs)
                session.commit()
            print(f"Inserted batch of {len(batch)} messages from Kafka.")
    finally:
        consumer.close()
    





    